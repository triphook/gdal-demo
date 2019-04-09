import os
import gdal
import numpy as np
import pandas as pd

# Path to the raster file
cdl_path = os.path.join("GIS", "nass_de", "cdl_30m_r_de_2016_utm18.tif")

# Open the file
cdl_raster = gdal.Open(cdl_path)

# Get raster geotransform (top_left_x, pixel_width, rotation, top_left_y, rotation, pixel_height)
left, cell_size, _, top, *_ = cdl_raster.GetGeoTransform()  # north up
shape = np.array([cdl_raster.RasterXSize, cdl_raster.RasterYSize])

# Extract a 3km by 3km piece of the land cover raster as an array
x_offset = 5000  # 10 km east from the western edge
y_offset = 5000  # 10 km south from the northern edge
x_max = 3000  # 3 km wide
y_max = 3000  # 3 km long
band = cdl_raster.GetRasterBand(1)  # 1 band raster
bounds = map(lambda x: int(x / cell_size), (x_offset, y_offset, x_max, y_max))  # meters -> pixels
sample = band.ReadAsArray(*bounds)

# Work with the array
print(sample)
print(sample.shape)

# Return the area for the land cover classes
cdl_table = pd.read_csv(os.path.join("GIS", "cdl_classes.csv")).set_index('cdl')
class_counts = np.array(np.unique(sample, return_counts=True)).T
class_table = pd.DataFrame(class_counts, columns=['cdl', 'pixels']).set_index('cdl')
class_table = class_table.merge(cdl_table, left_index=True, right_index=True)
class_table['area'] = np.int32(class_table.pop('pixels') * cell_size ** 2)
class_table['pct'] = (class_table.area / (x_max * y_max)) * 100
print(class_table.sort_values('pct', ascending=False))

# Write the array to a new raster
out_path = os.path.join("GIS", "test_square.tif")
driver = cdl_raster.GetDriver()
out_raster = driver.Create(out_path, int(x_max / cell_size), int(y_max / cell_size), 1, gdal.GDT_Int32)
out_raster.SetGeoTransform((left + x_offset, cell_size, 0, top - y_offset, 0, -cell_size))
out_band = out_raster.GetRasterBand(1)
out_band.WriteArray(sample, 0, 0)

