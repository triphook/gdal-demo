import numpy as np
import gdal


class Envelope(object):
    # Object representing a simple bounding rectangle, used primarily to measure raster overlap

    def __init__(self, left, right, bottom, top):
        self.left, self.right, self.bottom, self.top = map(float, (left, right, bottom, top))

    # Returns the rectangle corresponding to the overlap with another Envelope object
    def overlap(self, r2):
        if all(((self.left <= r2.right), (r2.left <= self.right), (self.bottom <= r2.top), (r2.bottom <= self.top))):
            left, right = sorted([self.left, self.right, r2.left, r2.right])[1:3]
            bottom, top = sorted([self.bottom, self.top, r2.bottom, r2.top])[1:3]
            return Envelope(left, right, bottom, top)
        else:
            print("Rasters do not overlap: {}\nAllocation: {}".format(self.shape, r2))

    def tiles(self, tile_size='max', progress=True):
        if tile_size == 'max':
            yield self
        else:
            x = list(range(int(self.left), int(self.right), tile_size)) + [self.right]
            y = list(range(int(self.bottom), int(self.top), tile_size)) + [self.top]
            total_tiles = (len(x) - 1) * (len(y) - 1)
            counter = iter(range(total_tiles))
            for i in range(len(x) - 1):
                for j in range(len(y) - 1):
                    if progress and total_tiles > 1:
                        print("Processing tile {} of {}".format(next(counter) + 1, total_tiles))
                    yield Envelope(*map(float, (x[i], x[i + 1], y[j], y[j + 1])))

    @property
    def area(self):
        return abs(self.top - self.bottom) * abs(self.right - self.left)

    def __eq__(self, other):
        return (self.left, self.right, self.bottom, self.top) == (other.left, other.right, other.bottom, other.top)


class Raster(object):
    def __init__(self, path, no_data=255):
        self.no_data = no_data
        self.obj = gdal.Open(path)
        left, self.cell_size, _, top, *_ = self.obj.GetGeoTransform()
        x_size, y_size = np.array([self.obj.RasterXSize, self.obj.RasterYSize]) * self.cell_size
        self.shape = Envelope(left, left + x_size, top - y_size, top)
        self.max_val = int(self.obj.GetRasterBand(1).ComputeRasterMinMax(1)[1])
        self.precision = 10 ** (int(np.log10(self.max_val)) + 1)
        self.values = np.where(np.array(self.obj.GetRasterBand(1).GetHistogram()) > 0)[0]
        self._array = np.array([])
        self.n_classes = len(self.values)
        self.array_envelope = self.shape

    def array(self, envelope=None, zero_min=True):
        if not self._array.size or envelope != self.array_envelope:
            offset_x, offset_y = (envelope.left - self.shape.left), (self.shape.top - envelope.top)
            x_max, y_max = (envelope.right - envelope.left), (envelope.top - envelope.bottom)
            bounds = map(lambda x: int(x / self.cell_size), (offset_x, offset_y, x_max, y_max))
            self._array = self.obj.ReadAsArray(*bounds)
            self._array[self._array == self.no_data] = 0
            if zero_min:
                self._array[self._array < 0] = 0
            if self.precision > 10000:
                self._array = np.int64(self._array)
            self.array_envelope = envelope
        return self._array
