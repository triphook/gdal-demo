import os
import gdal
import numpy as np


class GDALRaster(object):
    def __init__(self, path):
        self.obj = gdal.Open(path)
        self.left, self.cell_size, _, self.top, *_ = self.obj.GetGeoTransform()
        self.shape = np.array([self.obj.RasterXSize, self.obj.RasterYSize])
        self.x_size, self.y_size = self.shape * self.cell_size


class RasterSelection(object):
    def __init__(self, raster, x_offset=0, y_offset=0, x_max=0, y_max=0):
        # Set raster and pixel coordinates
        if not any((x_offset, y_offset, x_max, y_max)):  # whole raster
            x_max, y_max = raster.x_size, raster.y_size
        self.left = raster.left + x_offset
        self.top = raster.top - y_offset
        self.cell_size = raster.cell_size
        self.x_pixels = int(x_max / raster.cell_size)
        self.y_pixels = int(y_max / raster.cell_size)
        self.bounds = list(map(lambda x: int(x / self.cell_size), (x_offset, y_offset, x_max, y_max)))

        # Get driver from template raster
        self.driver = raster.obj.GetDriver()

        # Fetch the array
        band = raster.obj.GetRasterBand(1)  # 1 band raster
        self.array = band.ReadAsArray(*self.bounds)  # meters -> pixels

    def write(self, out_path):
        out_raster = self.driver.Create(out_path, self.x_pixels, self.y_pixels, 1, gdal.GDT_Int32)
        out_raster.SetGeoTransform((self.left, self.cell_size, 0, self.top, 0, -self.cell_size))
        out_band = out_raster.GetRasterBand(1)
        out_band.SetNoDataValue(0)
        out_band.WriteArray(self.array, 0, 0)
        out_band.FlushCache()


def make_tiles(x_size, y_size, tile_size):
    x = list(range(0, int(x_size), tile_size)) + [int(x_size)]
    y = list(range(0, int(y_size), tile_size)) + [int(y_size)]
    for i in range(len(x) - 1):
        for j in range(len(y) - 1):
            yield (x[i], y[j], x[i + 1] - x[i], y[j + 1] - y[j])


# Path to the raster file
cdl_path = os.path.join("..", "GIS", "nass_de", "cdl_30m_r_de_2016_utm18.tif")

# Initialize the CDL raster
cdl_raster = GDALRaster(cdl_path)

# Initialize a set of tiles to break up the raster
tile_size = 250000  # 25 km
tiles = make_tiles(cdl_raster.x_size, cdl_raster.y_size, tile_size)

# Save tiles
out_tile = os.path.join("..", "GIS", "tiles", "tile_{}.tif")
for counter, tile in enumerate(tiles):
    print(counter)
    sample = RasterSelection(cdl_raster, *tile)
    sample.write(out_tile.format(counter))

# Make a raster of corn pixels
corn_raster = os.path.join("..", "GIS", "tiles", "delaware_corn.tif")
sample = RasterSelection(cdl_raster)
sample.array[sample.array != 1] = 0
sample.write(corn_raster)
