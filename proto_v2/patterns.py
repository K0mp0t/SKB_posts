from PIL import ImageFilter
from .font_drawing import *
from .evaluatablegeneration_v2 import *
import random


def gen_simple_pattern(genImage, with_mask=False, text_size=(860, 64),
                       color=(0, 0, 0), text_outline_offset=0,
                       max_font_size=72, text_pos_x=100, max_fill=0.75,
                       threshold=0.6):
    results = []
    text = genImage.text
    model = genImage.model

    crop_index = 0
    for used_img, used_mask in zip(genImage.croped_images, genImage.croped_masks):
        result = used_img.copy()

        if with_mask:
            rgb_to_text_translation = {(0, 170, 19): 'mg', (255, 117, 0): 'mo', (151, 215, 0): 'lg',
                                       (255, 198, 0): 'yel', (224, 0, 77): 'cr'}

            colors = []
            for color in genImage.comp_colors:
                colors.append((color, rgb_to_text_translation[color]))
            random.shuffle(colors)

            bg_color, mask_color = colors[0][0], colors[0][1]

            bg = Image.new('RGBA', (1080, 1080), bg_color)
            form = Image.open(os.path.join(genImage.forms_root, f'1/mask_{mask_color}.png'))
            x, y = np.random.randint(0, 100), np.random.randint(550, 650)
            crop_size = np.random.randint(450, 700)
            cropped = form.crop((0, y, crop_size, y + crop_size)).resize((1080, 1080))
            bg.paste(cropped, box=(x, 0))

            used_mask[used_mask != 0] = 255
            filtered_mask = Image.fromarray(used_mask.astype(np.uint8)).resize((1080, 1080)).filter(ImageFilter.SMOOTH)

            result.paste(bg, mask=bg)
            result.paste(used_img, mask=filtered_mask)

        new_areas = []

        for i in range(len(genImage.empty_areas[crop_index])):
            (pos_x, pos_y), (size_x, size_y) = genImage.empty_areas[crop_index][i]
            available_size = size_x * max_fill
            min_fig_size = min(size_x, size_y) // 4

            if min_fig_size < 30:
                min_fig_size = 30

            max_fig_size = min_fig_size + 5
            fig_cnt = available_size // min_fig_size

            if fig_cnt < 2:
                continue

            if random.random() < max_fill:
                new_areas.append([(pos_x, pos_y), (size_x, size_y), (min_fig_size, max_fig_size, fig_cnt)])

        forms = []
        for (_, _), (size_x, size_y), (min_fig_size, max_fig_size, fig_cnt) in new_areas:
            forms.append(generate_good_image_wrapped(
                img_size=(size_y, size_x),
                model=model,
                forms_root=genImage.forms_root,
                fig_count=fig_cnt,
                forms_type='t',
                fig_size_range=(min_fig_size, max_fig_size),
                threshold=threshold))

        img_text, text_box = get_interview_image_text(text, genImage.fonts_root, text_y_offset=1)

        for form, area_info in zip(forms, new_areas):
            result.paste(form, area_info[0], form.convert('RGBA'))
        result.paste(img_text, (text_pos_x, text_box[1]-50), mask=img_text)

        results.append(result)
        crop_index += 1

    return results


def get_arrow_image_text(text, fonts_root, text_size=(860, 64),
                         color=(0, 0, 0), text_outline_offset=0,
                         max_font_size=72):
    text_width, text_height = text_size[0], text_size[1]

    img_text, lines_sizes = get_image_text(
        text_width,
        text_height,
        text,
        fonts_root,
        color=color,
        offset=text_outline_offset,
        max_font_size=max_font_size
    )

    return img_text


def find_lower_bound_of_text(lines_sizes, line_spacing):
    lower_bound = line_spacing * (len(lines_sizes) - 1)
    for line_size in lines_sizes:
        lower_bound += line_size[1]

    return lower_bound


def create_pattern_vacancy(text, forms_root, fonts_root):
    result = Image.new("RGBA", (1080, 1080))
    bg = Image.open(os.path.join(forms_root, '1/vacancy_bg.png'))
    vacancy = Image.open(os.path.join(forms_root, '1/vacancy.png'))
    img_text, lines_sizes = get_image_text(960, 450, text, fonts_root, font_type='b', color=(255, 255, 255),
                                           max_font_size=200)

    lower_bound = find_lower_bound_of_text(lines_sizes, int(lines_sizes[0][1]*1.2))

    result.paste(bg, box=(0, 0))
    result.paste(img_text, mask=img_text, box=(60, 375))
    result.paste(vacancy, mask=vacancy, box=(170, lower_bound + 330))

    return [result]


def create_pattern_vacancy_description(text, forms_root, fonts_root):
    """Args:
        text (:obj:`list`): Title of the text and the text itself.
        forms_root:
        fonts_root:
      Returns:
          PIL Image (:obj:`PIL.Image.Image`)

      """
    result = Image.new("RGBA", (1080, 1080), (255, 255, 255))

    img_text, lines_sizes = get_image_text(900, 76, text[0], fonts_root, font_type='b', color=(0, 0, 0),
                                           max_font_size=64)
    result.paste(img_text, mask=img_text, box=(90, 110))

    marker = Image.open(os.path.join(forms_root, 'cm_r_yel.png'))
    marker.thumbnail((29, 46))
    lower_bound = 255

    for i in text[1:]:
        result.paste(marker, mask=marker, box=(90, lower_bound))
        img_text, lines_sizes = get_image_text(846, 192, i, fonts_root, color=(0, 0, 0), max_font_size=48)
        result.paste(img_text, mask=img_text, box=(144, lower_bound))

        line_spacing = int(lines_sizes[0][1] * 1.2)

        lower_bound += find_lower_bound_of_text(lines_sizes, line_spacing)
        lower_bound += 64

    color = random.choice(["cr", "lg", "mg", "mo", "yel"])
    cm = Image.open(os.path.join(forms_root, f'cm_r_{color}.png'))
    cm.thumbnail((69, 110))
    result.paste(cm, mask=cm, box=(951, 910))

    return [result]


def create_triple_checkmarks(comp_colors, forms_root):
    result = Image.new("RGBA", (136, 195))

    rgb_to_text_translation = {(0, 170, 19): 'mg', (255, 117, 0): 'mo', (151, 215, 0): 'lg', (255, 198, 0): 'yel',
                               (224, 0, 77): 'cr'}

    colors = []
    for color in comp_colors:
        colors.append(rgb_to_text_translation[color])
    random.shuffle(colors)

    cm1 = Image.open(os.path.join(forms_root, f'cm_r_{colors[0]}.png'))
    cm1.thumbnail((27, 43))
    result.paste(cm1, mask=cm1, box=(40, 0))

    cm2 = Image.open(os.path.join(forms_root, f'cm_l_{colors[1]}.png'))
    cm2.thumbnail((40, 65))
    result.paste(cm2, mask=cm2, box=(95, 52))

    cm3 = Image.open(os.path.join(forms_root, f'cm_r_{colors[2]}.png'))
    cm3.thumbnail((54, 86))
    result.paste(cm3, mask=cm3, box=(0, 109))

    return result


def create_pattern_checkmarks(genImage):
    results = []

    for used_img, used_mask in zip(genImage.croped_images, genImage.croped_masks):
        used_mask[used_mask != 0] = 255
        filtered_mask = (Image.fromarray(used_mask.astype(np.uint8)).resize((1080, 1080))).filter(ImageFilter.SMOOTH)

        result = used_img.copy()
        result.paste(used_img, mask=filtered_mask)

        img_text, lines_sizes = get_image_text(780, 172, genImage.text, genImage.fonts_root, font_type='b',
                                               color=(255, 255, 255), max_font_size=72)

        line_spacing = int(lines_sizes[0][1] * 1.2)

        lower_bound_text = find_lower_bound_of_text(lines_sizes, line_spacing)
        result.paste(img_text, mask=img_text, box=(110, 1080 - 60 - lower_bound_text))

        triple_checkmarks = create_triple_checkmarks(genImage.get_comp_colors(n_colors=3), genImage.forms_root)
        result.paste(triple_checkmarks, mask=triple_checkmarks, box=(884, 825))

        results.append(result)

    return results


def create_pattern_header_at_top_checkmarks(text, forms_root, fonts_root, color='g'):
    """Args:
          text (:obj:`str`): Title text.
          color (:obj:`str`): Сheckmark color ('g' - green, 'dmo' - dark orange, 'lmo' - light orange). Defaults to 'g'.
          forms_root:
          fonts_root:

      Returns:
          PIL Image (:obj:`PIL.Image.Image`)

      """

    result = Image.new("RGBA", (1080, 1080), (255, 255, 255))

    words = text.split()
    t1 = ''
    for i in range(len(words)):
        if len(t1 + words[i]) <= 17 and i != len(words) - 1:
            t1 += words[i] + ' '
    t2 = text[len(t1):]

    flag = True

    if t1 == '':
        t1 = t2
        flag = False

    img_text1, lines_sizes1 = get_image_text(860, 106, t1, fonts_root, font_type='b', color=(0, 0, 0), max_font_size=90)
    result.paste(img_text1, mask=img_text1, box=(110, 110))

    if flag:
        img_text2, lines_sizes2 = get_image_text(860, 106, t2, fonts_root, font_type='b', color=(0, 170, 19)
                                                 if color == 'g' else (255, 117, 0), max_font_size=90)
        result.paste(img_text2, mask=img_text2, box=(110, lines_sizes1[0][1] + 110))

    checkmarks = Image.open(os.path.join(forms_root, f'1/checkmarks_big_{color}.png'))
    result.paste(checkmarks, mask=checkmarks, box=(0, 459))

    return [result]


def create_double_checkmarks(forms_root, color='g'):
    result = Image.new("RGBA", (129, 110))
    colors = ['lg', 'mg'] if color == 'g' else ['yel', 'mo']

    cm1 = Image.open(os.path.join(forms_root, f'cm_l_{colors[0]}.png'))
    cm1.thumbnail((69, 110))
    result.paste(cm1, mask=cm1, box=(0, 0))

    cm2 = Image.open(os.path.join(forms_root, f'cm_l_{colors[1]}.png'))
    cm2.thumbnail((69, 110))
    result.paste(cm2, mask=cm2, box=(60, 0))

    return result


def create_pattern_interview_text(text, forms_root, fonts_root, color='g'):
    """Args:
          text (:obj:`list`): Title of the text and the text itself.
          color (:obj:`str`): Color of checkmarks and letters on the background ('g' - green, 'o' - orange) Default: 'g'
          forms_root:
          fonts_root:

      Returns:
          PIL Image (:obj:`PIL.Image.Image`)
      """

    result = Image.new("RGBA", (1080, 1080), (255, 255, 255))

    img_text, lines_sizes1 = get_image_text(1330, 1000, text[0][:2], fonts_root, font_type='b', color=(151, 215, 0, 30)
                                            if color == 'g' else (255, 117, 0, 30), max_font_size=1000)
    result.paste(img_text, mask=img_text, box=(-100, -287))

    img_text, lines_sizes1 = get_image_text(860, 76, text[0], fonts_root, font_type='b', color=(0, 0, 0),
                                            max_font_size=64)
    result.paste(img_text, mask=img_text, box=(110, 110))

    img_text, lines_sizes1 = get_image_text(860, 912, text[1], fonts_root, color=(0, 0, 0), max_font_size=52)
    result.paste(img_text, mask=img_text, box=(110, 186))

    double_checkmarks = create_double_checkmarks(color, forms_root)

    result.paste(double_checkmarks, mask=double_checkmarks, box=(891, 1181))

    return [result]


def get_round_mask_image(img, face_size, mask_offset='auto'):
    mask = Image.new("L", img.size, 255)

    if mask_offset == 'auto':
        offset = (face_size ** 2 / (img.size[0] * img.size[1])) \
                 * min(img.size[0], img.size[1]) / 2
    else:
        offset = mask_offset

    bbox = (0 + offset, 0 + offset,
            img.size[0] - offset, img.size[1] - offset)
    draw = ImageDraw.Draw(mask)
    draw.ellipse(bbox, fill=0)

    back = Image.new('RGB', img.size, (255, 255, 255))

    return Image.composite(back, img, mask)


def get_color_mask_image(img, mask, mask_offset=40,
                         bg_colors=None):
    if bg_colors is None:
        bg_colors = [(224, 0, 77), (255, 117, 0), (255, 198, 0)]
    bg = Image.new('RGBA', img.size, (0, 0, 0, 0))

    if mask_offset == 'auto':
        mask_offset = 40

    offsets = [(mask_offset, 0), (-mask_offset, 0), (0, -mask_offset)]

    for color, offset in zip(bg_colors, offsets):
        colored_bg = Image.new('RGB', img.size, color)
        bg.paste(colored_bg, offset, mask)

    bg.paste(img.convert('L'), mask=mask.filter(ImageFilter.BLUR))

    return bg


def get_interview_image_text(text, fonts_root, image_size=(1080, 1080), text_relative_size=(0.8, 0.2),
                             color=(255, 255, 255), text_outline_offset=10, max_font_size=90,
                             text_y_offset=2.0):
    text_width, text_height = round(image_size[0] * text_relative_size[0]), round(image_size[1] * text_relative_size[1])

    img_text, lines_sizes = get_image_text(
        text_width,
        text_height,
        text,
        fonts_root,
        color=color,
        offset=text_outline_offset,
        max_font_size=max_font_size
    )

    max_line_width = sorted(lines_sizes, key=(lambda line: line[0]), reverse=True)[0][0]
    lines_height = sum([line_size[1]*1.2 for line_size in lines_sizes]) + text_outline_offset * 2

    text_box = round(max_line_width / 8), round(image_size[1] - lines_height * text_y_offset)

    return img_text, text_box


def gen_interview_pattern(genImage, pattern_type='round', cropped_image_index=1,
                          mask_offset='auto', text_relative_size=(0.8, 0.2),
                          text_y_offset=1.25, text_color=(255, 255, 255),
                          max_font_size=200, text_outline_offset=10):
    img = genImage.croped_images[cropped_image_index].copy()
    if pattern_type == 'round':
        # if len(genImage.faces_on_croped[cropped_image_index]) > 0:
        #     face_size = genImage.faces_on_croped[cropped_image_index][0][2]
        # else:
        #     face_size = None
        #     mask_offset = 80
        face_size = 120
        img_with_mask = get_round_mask_image(img, face_size, mask_offset)
    else:
        mask = genImage.croped_masks[cropped_image_index].astype('uint8')
        mask[mask > 0] = 255
        mask = Image.fromarray(mask).resize(img.size).filter(ImageFilter.BLUR)

        img_with_mask = get_color_mask_image(img, mask)

    img_text, text_box = get_interview_image_text(genImage.text, genImage.fonts_root, img.size, text_relative_size,
                                                  text_color, text_outline_offset,
                                                  max_font_size, text_y_offset)

    img_with_mask.paste(img_text, text_box, img_text)

    paths = [os.path.join(genImage.forms_root, x) for x in os.listdir(genImage.forms_root)
             if 'triangle_br' in x
             and 's' not in x
             and 'big' not in x
             and os.path.isfile(os.path.join(genImage.forms_root, x))]

    triangle = Image.open(paths[np.random.randint(0, len(paths))]).resize((112, 112))

    triangle_box = (text_box[0], text_box[1] - 112)

    img_with_mask.paste(triangle, triangle_box, triangle)

    return [img_with_mask]
