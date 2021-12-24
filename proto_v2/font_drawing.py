from PIL import ImageFont, ImageDraw, Image
import os

FONT = 'muller.ttf'
FONT_B = 'muller_b.ttf'
FONT_L = 'muller_l.ttf'


def get_text_size(font_filename, font_size, text):
    font = ImageFont.truetype(font_filename, font_size)
    return font.getsize(text)


def get_font_size(text, font, max_width=None, max_height=None):
    if max_width is None and max_height is None:
        raise ValueError('You need to pass max_width or max_height')
    font_size = 1
    text_size = get_text_size(font, font_size, text)
    if (max_width is not None and text_size[0] > max_width) or \
            (max_height is not None and text_size[1] > max_height):
        raise ValueError("Text can't be filled in only (%dpx, %dpx)" % \
                         text_size)
    while True:
        if (max_width is not None and text_size[0] >= max_width) or \
                (max_height is not None and text_size[1] >= max_height):
            return font_size - 1
        font_size += 1
        text_size = get_text_size(font, font_size, text)


class ImageText(object):
    def __init__(self, image_or_size, mode='RGBA', background=(0, 0, 0, 0),
                 encoding='utf8'):
        if isinstance(image_or_size, Image.Image):
            self.filename = None
            self.image = image_or_size
            self.size = self.image.size
        elif isinstance(image_or_size, (list, tuple)):
            self.size = image_or_size
            self.image = Image.new(mode, self.size, color=background)
            self.filename = None
        self.draw = ImageDraw.Draw(self.image)
        self.encoding = encoding

    def save(self, filename=None):
        self.image.save(filename or self.filename)

    def write_text(self, x, y, text, font_filename, font_size=11,
                   color=(0, 0, 0), max_width=None, max_height=None, line_spacing=0):
        if font_size == 'fill' and \
                (max_width is not None or max_height is not None):
            font_size = get_font_size(text, font_filename, max_width, max_height)
        text_size = get_text_size(font_filename, font_size, text)
        font = ImageFont.truetype(font_filename, font_size)
        if x == 'center':
            x = (self.size[0] - text_size[0]) / 2
        if y == 'center':
            y = (self.size[1] - text_size[1]) / 2
        self.draw.text((x, y), text, font=font, fill=color)
        return text_size

    def write_text_box(self, x, y, text, box_width, box_height, font_filename, line_spacing=0,
                       font_size=11, color=(0, 0, 0), place='left',
                       justify_last_line=False):
        words = text.split()
        while True:
            lines = []
            line = []
            lines_sizes = []
            fitting_failed = False
            for word in words:
                new_line = ' '.join(line + [word])
                size = get_text_size(font_filename, font_size, new_line)
                text_height = size[1]
                if size[0] <= box_width:
                    line.append(word)
                else:
                    lines.append(line)
                    size = get_text_size(font_filename, font_size, ' '.join(line))
                    if (len(line) == 1 and size[0] > box_width) or len(lines) * text_height > box_height:
                        font_size -= 1
                        fitting_failed = True
                        break
                    lines_sizes.append((size[0], size[1]))
                    line = [word]
            size = get_text_size(font_filename, font_size, ' '.join(line))
            text_height = size[1]

            if fitting_failed:
                continue
            if line:
                lines.append(line)
                size = get_text_size(font_filename, font_size, ' '.join(line))
                lines_sizes.append((size[0], size[1]))
            if size[0] > box_width or len(lines) * text_height > box_height:
                font_size -= 1
                continue
            break
        while len(lines) * text_height + (len(lines) - 1) * line_spacing > box_height:
            line_spacing -= 1
        lines = [' '.join(line) for line in lines if line]
        height = y - line_spacing - text_height
        for index, line in enumerate(lines):
            height += text_height + line_spacing
            if place == 'left':
                self.write_text(x, height, line, font_filename, font_size,
                                color)
            elif place == 'right':
                total_size = get_text_size(font_filename, font_size, line)
                x_left = x + box_width - total_size[0]
                self.write_text(x_left, height, line, font_filename,
                                font_size, color)
            elif place == 'center':
                total_size = get_text_size(font_filename, font_size, line)
                x_left = int(x + ((box_width - total_size[0]) / 2))
                self.write_text(x_left, height, line, font_filename,
                                font_size, color)
            elif place == 'justify':
                words = line.split()
                if (index == len(lines) - 1 and not justify_last_line) or \
                        len(words) == 1:
                    self.write_text(x, height, line, font_filename, font_size,
                                    color)
                    continue
                line_without_spaces = ''.join(words)
                total_size = get_text_size(font_filename, font_size,
                                           line_without_spaces)
                space_width = (box_width - total_size[0]) / (len(words) - 1.0)
                start_x = x
                for word in words[:-1]:
                    self.write_text(start_x, height, word, font_filename,
                                    font_size, color)
                    word_size = get_text_size(font_filename, font_size,
                                              word)
                    start_x += word_size[0] + space_width
                last_word_size = get_text_size(font_filename, font_size,
                                               words[-1])
                last_word_x = x + box_width - last_word_size[0]
                self.write_text(last_word_x, height, words[-1], font_filename,
                                font_size, color)
        return lines_sizes, line_spacing


def get_image_text(width, height, text, fonts_root, font_type=None, max_font_size=70,
                   max_line_spacing=0, place='left', color=(128, 128, 128), offset=0, bg_color=(0, 0, 0)):
    """Args:
          width (:obj:`int`): Width of the image_text.
          height (:obj:`int`): Height of the image_text.
          text (:obj:`str`): Text to draw.
          fonts_root:
          font_type (:obj:`str`): Type of the font (None - regular, 'b' - bold, 'l' - light). Defaults to None.
          max_font_size (:obj:`int`): Maximum possible font size. Defaults to 70.
          max_line_spacing (:obj:`int`): Maximum possible line spacing. Defaults to 0.
          place (:obj:`str`): Text placement ('left', 'right', 'center', 'justify').
          color (:obj:`tuple`): Text color (r, g, b). Defaults to (128, 128, 128).
          offset (:obj:`int`): Background offset. Background will be drawn if offset > 0.
          bg_color (:obj:`tuple`): Background color (r, g, b). Defaults to (0, 0, 0).

      Returns:
          PIL Image (:obj:`PIL.Image.Image`), Lines Sizes (:obj:`tuple`), Line Spacing (:obj:`int`)


      """
    img = ImageText((width, height), background=(255, 255, 255, 0))

    lines_sizes, line_spacing = img.write_text_box(
        0, 0,
        text,
        box_width=width,
        box_height=height,
        font_filename=os.path.join(fonts_root, FONT_B) if font_type == 'b' else os.path.join(fonts_root, FONT_L)
        if font_type == 'l' else os.path.join(fonts_root, FONT),
        line_spacing=max_line_spacing,
        font_size=max_font_size,
        color=color,
        place=place
    )

    if offset > 0:
        offset = 10

        img_back = Image.new('RGBA', (width + offset * 2, height + offset * 2))
        draw = ImageDraw.Draw(img_back)

        line_x, line_y = offset, offset
        for size in lines_sizes:
            draw.rectangle(
                [(line_x - offset, line_y - size[1] // 4),
                 (size[0] + line_x + offset, size[1] + line_y + size[1] // 2)],
                fill=bg_color
            )
            line_y += size[1] + line_spacing

        img_back.alpha_composite(img.image, (offset, offset))

        return img_back if offset > 0 else img.image, lines_sizes, line_spacing
    return img.image, lines_sizes, line_spacing
