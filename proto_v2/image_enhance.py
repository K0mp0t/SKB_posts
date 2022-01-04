from PIL import ImageEnhance


class Enhancer:
    """
    Class to run enhancing using PIL
    """

    def __init__(self, image):
        self._brightness_enhance = ImageEnhance.Brightness(image)
        self._contrast_enhance = ImageEnhance.Contrast(image)
        self._color_enhance = ImageEnhance.Color(image)
        self._sharpness_enhance = ImageEnhance.Sharpness(image)
        self._original_image = image
        self._latest_image = image

    def change_brightness(self, factor=1):
        self._latest_image = self._brightness_enhance.enhance(factor)
        return self._latest_image

    def change_contrast(self, factor=1):
        self._latest_image = self._contrast_enhance.enhance(factor)
        return self._latest_image

    def change_color(self, factor=1):
        self._latest_image = self._color_enhance.enhance(factor)
        return self._latest_image

    def change_sharpness(self, factor=1):
        self._latest_image = self._sharpness_enhance.enhance(factor)
        return self._latest_image

    def apply_all(self,
                  brightness_factor, contrast_factor,
                  color_factor, sharpness_factor):
        """
        Parameters:
          factors of transform
        Return:
          image with all applied enhances  
        """
        img = self.change_brightness(brightness_factor)
        contrast_enhancer = ImageEnhance.Contrast(img)
        img = contrast_enhancer.enhance(contrast_factor)
        color_enhancer = ImageEnhance.Color(img)
        img = color_enhancer.enhance(color_factor)
        sharpness_enhancer = ImageEnhance.Sharpness(img)
        img = sharpness_enhancer.enhance(sharpness_factor)
        return img


def get_mean(mask):
    """
     Parameters:
       mask
     Return:
       mean value of all nonzero coordinates  
     """
    mean = None
    for x in range(mask.shape[0]):
        for y in range(mask.shape[1]):
            if mask[x][y] > 0:
                if mean:
                    mean = ((mean[0] + x) / 2, (mean[1] + y) / 2)
                else:
                    mean = (int(x), int(y))
    if not mean:
        mean = (1080 // 2, 1080 // 2)
    return mean


def get_scale(img, mask):
    """
    Return:
      scale of image to mask
    """
    scale = max(img.size) / max(mask.shape)
    return scale


def get_object_coordinates(object_mask):
    nonzero_indices = object_mask.nonzero()

    return [nonzero_indices[0].min(), nonzero_indices[0].max(), nonzero_indices[1].min(), nonzero_indices[1].max()]


def get_points(obj_coordinates, size, center_image, basesize, center):
    """
    Parameters:
      obj_coordinates:
      size: size of image or mask
      center_image (bool): use center of image as mean
      basesize
      center: overrides if center_image is True
    Return:
      three upper left point of thirds 
    """
    if center_image:
        center = (size[0] // 2, size[1] // 2)

    first = max(center) - (basesize // 3)
    mid = max(center) - basesize // 2
    third = max(center) - (2 * basesize // 3)

    if mid < 0:
        mid = 0
    elif mid > obj_coordinates[0] or mid + basesize < obj_coordinates[1]:
        mid = (sum(obj_coordinates) / 2) - (basesize // 2)
        if mid > obj_coordinates[0]:
            mid -= obj_coordinates[0] - 50
        elif mid + basesize < obj_coordinates[1]:
            mid += basesize - obj_coordinates[1] + 50

    if first < 0:
        first = 0
    elif first > obj_coordinates[0]:
        first = obj_coordinates[0]
    if first + basesize > max(size):
        first = max(size) - basesize

    if third < 0:
        third = 0
    elif third > obj_coordinates[0]:
        third = obj_coordinates[0]
    if third + basesize > max(size):
        third = max(size) - basesize

    return int(first), int(mid), int(third)


def crop_by_sqare(mask, coordinates=None, img=None, center_image: bool = False, scale=1, basesize=1080):
    """
    Parameters:
      coordinates:
      basesize:
      mask
      img (optioal): optioal
      center_image (bool): use center of image as mean
      scale: scale of image to mask
    Return:
      tuple of images croped by thirds
    """
    mean = get_mean(mask)
    if img is not None:
        coordinates = [int(x * scale) for x in coordinates]
        center = (mean[1] * scale, mean[0] * scale)
        first, mid, third = get_points(coordinates, img.size[:2], center_image, basesize, center)
        if img.size[0] >= img.size[1]:
            return (img.crop((first, 0, first + basesize, basesize)),
                    img.crop((mid, 0, mid + basesize, basesize)),
                    img.crop((third, 0, third + basesize, basesize)))
        else:
            return (img.crop((0, first, basesize, first + basesize)),
                    img.crop((0, mid, basesize, mid + basesize)),
                    img.crop((0, third, basesize, third + basesize)))
    else:
        scaled_basesize = int(basesize / scale)
        center = (mean[1] * scale, mean[0] * scale)
        first, mid, third = get_points(coordinates, (mask.shape[1], mask.shape[0]), center_image, scaled_basesize, center)
        if mask.shape[1] >= mask.shape[0]:
            return (mask[0:scaled_basesize, first:first + scaled_basesize],
                    mask[0:scaled_basesize, mid:mid + scaled_basesize],
                    mask[0:scaled_basesize, third:third + scaled_basesize])
        else:
            return (mask[first:first + scaled_basesize, 0:scaled_basesize],
                    mask[mid:mid + scaled_basesize, 0:scaled_basesize],
                    mask[third:third + scaled_basesize, 0:scaled_basesize])
