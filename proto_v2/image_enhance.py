from PIL import ImageEnhance
import numpy as np


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
    if any(x.size == 0 for x in nonzero_indices):
        return list([0, 0, object_mask.shape[0], object_mask.shape[1]])

    return [nonzero_indices[0].min(), nonzero_indices[0].max(), nonzero_indices[1].min(), nonzero_indices[1].max()]


def get_points(obj_coordinates, size, basesize):
    """
    Parameters:
      obj_coordinates:
      size: size of image or mask
      basesize
    Return:
      three upper left point of thirds 
    """
    first = obj_coordinates[0] + basesize // 20
    mid = obj_coordinates[0] / 2
    third = obj_coordinates[1] - basesize // 20 * 18

    if first < 0:
        first = 0
    elif first + basesize > max(size):
        first = max(size) - basesize

    if mid < 0:
        mid = 0
    elif mid + basesize > max(size):
        mid = max(size) - basesize

    if third < 0:
        third = 0
    elif third + basesize > max(size):
        third = max(size) - basesize

    return int(first), int(mid), int(third)


def crop_by_sqare(mask, coordinates=None, img=None, scale=1, basesize=1080):
    """
    Parameters:
      coordinates:
      basesize:
      mask
      img (optioal): optioal
      scale: scale of image to mask
    Return:
      tuple of images croped by thirds
    """
    mean = get_mean(mask)
    if img is not None:
        coordinates = [int(x * scale) for x in coordinates]
        first, mid, third = get_points(coordinates, img.size[:2],  basesize)
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
        first, mid, third = get_points(coordinates, (mask.shape[1], mask.shape[0]), scaled_basesize)
        if mask.shape[1] >= mask.shape[0]:
            return (mask[0:scaled_basesize, first:first + scaled_basesize],
                    mask[0:scaled_basesize, mid:mid + scaled_basesize],
                    mask[0:scaled_basesize, third:third + scaled_basesize])
        else:
            return (mask[first:first + scaled_basesize, 0:scaled_basesize],
                    mask[mid:mid + scaled_basesize, 0:scaled_basesize],
                    mask[third:third + scaled_basesize, 0:scaled_basesize])
