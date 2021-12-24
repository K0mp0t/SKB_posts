from PIL import Image
import os.path as osp
import numpy as np


class ImageGrid(object):
    """Implements image grid that allows to assemble image from parts

    """

    __height = 200
    __width = 200
    __map = np.zeros((200, 200))
    __forms = list()
    __coordinates = list()

    def __init__(self, height, width):
        self.__height = height
        self.__width = width
        self.__map = np.zeros((height, width))
        self.__forms = list()
        self.__coordinates = list()  # (x1, y1, x2, y2)    !!!(y1, x1, y2, x2)!!!

    def get_size(self):
        """Canvas size getter

        Returns:
          tuple (height, width) which represents canvas size
        """
        return self.__height, self.__width

    def get_intersection(self, image, coordinates):
        """Calculates intersection between new image which is being placed on canvas and canvas elements.
           Since images may have transparent pixels this func considers:
           1. Stacking images on transparent canvas parts
           2. Stacking images on non-transparent canvas parts in way that won't affect origin canvas

           Intersection is calculated with non-zero pixels sum comparison

           Args:
            image: PIL.Image, image to check intersection with
            coordinates: tuple, (x1, y1, x2, y2), coordinates to stack on

           Returns:
            boolean, True if there is an intersection

        """

        map_slice = self.render_slice(coordinates)
        size = (coordinates[3] - coordinates[1], coordinates[2] - coordinates[0])
        image_matrix = np.array(image.resize(size)).sum(axis=2)
        if map_slice.any():
            map_slice_nonzero = np.count_nonzero(map_slice)
            image_matrix_nonzero = np.count_nonzero(image_matrix)
            sum_nonzero = np.count_nonzero(np.add(map_slice, image_matrix))
            return map_slice_nonzero + image_matrix_nonzero != sum_nonzero
        else:
            return False

    def add_image(self, image, coordinates):
        """Adds an image to canvas if it has no intersection

           Args:
            image: PIL.Image, image to add
            coordinates: tuple, (x1, y1, x2, y2), coordinates to add image on

           Raises:
            ValueError if canvas has an intersection on given coordinates with given picture

        """
        if not self.get_intersection(image, coordinates):
            self.__forms.append(image.convert('RGBA'))
            self.__coordinates.append(coordinates)
            self.__map[coordinates[0]: coordinates[2], coordinates[1]: coordinates[3]] = len(self.__forms)
        else:
            raise ValueError(
                'there is an intersection between __map and new image, try to alter size and/or __coordinates')

    def render_slice(self, coordinates):
        """Renders slice (partial matrix) of image

           Args:
            coordinates: tuple, (x1, y1, x2, y2), coordinates of image part to render

           Returns:
            np.array that represents part of image in RGBA of RGB
        """
        img = np.array(self.render_image(self.__height, self.__width)).sum(axis=2)
        img_slice = img[coordinates[0]: coordinates[2], coordinates[1]: coordinates[3]]
        return img_slice

    def render_image(self, output_height=None, output_width=None):
        """Renders image. Basically just stacks images on given coordinates

           Args:
            output_height: int, canvas height to render
            output_width: int, canvas width to render

           Returns:
            PIL.Image that represents canvas with given size
        """

        if output_height is None or output_width is None:
            output_height = self.__height
            output_width = self.__width

        output_image = np.zeros((output_height, output_width, 4))

        height_coef = output_height / self.__height
        width_coef = output_width / self.__width
        for i in range(len(self.__forms)):
            scaled_c = (int(self.__coordinates[i][0] * width_coef),
                        int(self.__coordinates[i][1] * height_coef),
                        int(self.__coordinates[i][2] * width_coef),
                        int(self.__coordinates[i][3] * height_coef))
            size = (scaled_c[2] - scaled_c[0], scaled_c[3] - scaled_c[1])

            output_image[scaled_c[0]: scaled_c[2], scaled_c[1]: scaled_c[3]] += self.__forms[i].resize(
                (size[1], size[0]), Image.ANTIALIAS)

        return Image.fromarray(output_image.astype(np.uint8))


class ImageGenerator(object):
    __paths = list()
    __size = (0, 0)
    __figures = list()
    __fig_count = 0
    __fig_size_range = (0, 0)

    def get_paths(self):
        return self.__paths

    def __init__(self, paths, img_size, fig_count, fig_size_range):
        self.__paths = list()
        self.__figures = list()
        self.__size = img_size
        self.__fig_count = fig_count
        self.__fig_size_range = fig_size_range

        for path in paths:
            if osp.exists(path):
                self.__paths.append(path)
                self.__figures.append(Image.open(path).convert('RGBA'))
            else:
                raise ValueError(f'{path} doesn\'t exist')

    def __iter__(self):
        return self

    def __next__(self):
        return self._get_random_image()

    def _get_random_image(self):  # Если картинки могут заходить друг на друга, то distance_range=-1
        image_grid = ImageGrid(self.__size[0], self.__size[1])

        checked_points = []
        centers = []
        i = 0

        x, y = 0, 0

        while i < self.__fig_count:
            i += 1
            iterations = 0

            random_idx = np.random.randint(len(self.__figures))
            fig = self.__figures[random_idx]
            aspect_ratio = fig.size[0] / fig.size[1]

            x_size = np.random.randint(self.__fig_size_range[0], self.__fig_size_range[1])
            y_size = int(x_size * aspect_ratio)

            x_max = self.__size[0] - int(self.__fig_size_range[0] * aspect_ratio)
            y_max = self.__size[1] - self.__fig_size_range[0]

            while iterations < 200:
                x = np.random.randint(0, x_max)
                y = np.random.randint(0, y_max)

                if x + x_size < self.__size[0] and y + y_size < self.__size[1]:
                    if (
                            (x, y) not in checked_points and
                            not image_grid.get_intersection(fig, (x, y, x + x_size, y + y_size))
                    ):
                        break
                checked_points.append((x, y))

                iterations += 1

            if iterations >= 200:
                image_grid = ImageGrid(self.__size[0], self.__size[1])

                checked_points = []
                centers = []
                i = 0

                continue

            centers.append((x + x_size / 2, y + y_size / 2))
            image_grid.add_image(fig, (x, y, x + x_size, y + y_size))

        return image_grid.render_image()