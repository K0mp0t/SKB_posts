from PIL import ImageOps
import os
from tensorflow.keras.applications.efficientnet import preprocess_input
from .complexforms_v2 import *


def resize_image_with_pad(image, size=(150, 150)):
    """Resizes image to given size with padding if needed
    Args:
      image: PIL.Image or np.ndarray
      size: tuple, which represents target size, default = (150, 150)
    Returns:
      resized image as PIL.Image
    """
    if not isinstance(image, Image.Image):
        image = Image.fromarray(image)

    if image.size[0] == image.size[1]:
        image = image.resize(size)

    else:
        max_side = max(image.size)

        d_width = abs(image.size[0] - max_side)
        d_height = abs(image.size[1] - max_side)

        pad_width = d_width // 2
        pad_height = d_height // 2

        padding = (pad_width, pad_height, d_width - pad_width, d_height - pad_height)

        image = ImageOps.expand(image, padding).resize(size)

    return image


def alpha_to_color(image, color=(255, 255, 255)):
    """Converts RGBA images to RGB with correct transparent background transform
    Args:
      image: PIL.Image
      color: tuple, represents color for transparent background substitution
    Returns:
      RGB image, PIL.Image class object
    """
    image.load()  # needed for split()
    background = Image.new('RGB', image.size, color)
    background.paste(image, mask=image.split()[3])  # 3 is the alpha channel
    return background


def generate_good_image(generator, model, threshold=0.5):
    """Generates compositionally well-done image
    Args:
      generator: ImageGenerator object, generator to user
      model: tf.Model object, decision model
      threshold: float between 0 and 1, which limits output image score
    Returns:
      tuple, (PIL.Image, float) - image and its score
    """
    y_pred = 0
    img = None
    iterations = 0

    while y_pred < threshold:
        iterations += 1

        if iterations > 10:
            break

        img = next(generator)
        x = alpha_to_color(img)
        x = resize_image_with_pad(x, model.input_shape[1: 3])
        x = np.array([np.array(x)])
        x = preprocess_input(x)
        y_pred = model.predict(x)[0][0]

    return img


def generate_good_image_wrapped(img_size, model, forms_root, forms_type='all', fig_count=3, fig_size_range=(20, 65),
                                threshold=0.75):
    """Generate good image function wrapper
    Args:
      img_size: tuple, image size
      model:
      forms_root:
      forms_type: string, type of forms used in generation: c for checkmarks, t for triangles, rest for all
      fig_count: count of figures to generate, default = 3
      fig_size_range: tuple, range of figure sizes, default = (20, 65)
      model: keras.models.Sequential, scorer model
      threshold: float between 0 and 1, which limits output image score
    Returns:
      PIL.Image, generated image
    """

    if forms_type == 'c':
        paths = [os.path.join(forms_root, x) for x in os.listdir(forms_root) if
                 'cm' in x and os.path.isfile(os.path.join(forms_root, x))]
    elif forms_type == 't':
        paths = [os.path.join(forms_root, x) for x in os.listdir(forms_root) if
                 'triangle' in x and 's' not in x and 'big' not in x and os.path.isfile(os.path.join(forms_root, x))]
    else:
        paths = [os.path.join(forms_root, x) for x in os.listdir(forms_root) if
                 'big' not in x and os.path.isfile(os.path.join(forms_root, x))]

    generator = ImageGenerator(paths, img_size, fig_count, fig_size_range)

    img = generate_good_image(generator, model, threshold)

    del model, generator  # TEMP, rewrite as class

    return img
