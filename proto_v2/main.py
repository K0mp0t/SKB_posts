import io
from functools import partial
from proto_v2 import comp_colors, image_enhance, patterns, segmentation
from PIL import Image


class GenImage:
    def __init__(self, image_bytes, model, forms_root, fonts_root, seg_model_path, text=None):
        self.text = text
        self.basesize = 1080
        self.image_bytes = image_bytes
        self.image = Image.open(io.BytesIO(image_bytes))
        self.seg_model_path = seg_model_path
        self.forms_root = forms_root
        self.fonts_root = fonts_root

        wpercent = (self.basesize / float(min(self.image.size[:2])))
        hsize = int((float(max(self.image.size[:2])) * float(wpercent)))
        if self.image.size[0] < self.image.size[1]:
            self.image = self.image.resize((self.basesize, hsize), Image.ANTIALIAS)
        else:
            self.image = self.image.resize((hsize, self.basesize), Image.ANTIALIAS)

        self.mask = None
        self.original_image = None

        self.enhancer = image_enhance.Enhancer(self.image)
        self.enhancer_factors = {'britness_factor': 1,
                                 'contrast_factor': 1,
                                 'color_factor': 1,
                                 'sharpness_factor': 1}

        self.generate_image_mask()

        self.croped_images = None
        self.croped_masks = None
        self.empty_areas = None
        self.faces_on_croped = None
        self.comp_colors = None
        self.scale = image_enhance.get_scale(self.image, self.mask)

        obj_coordinates = image_enhance.get_object_coordinates(self.mask)
        if self.image.size[1] > self.image.size[0]:
            self.obj_coordinates = obj_coordinates[:2]
        else:
            self.obj_coordinates = obj_coordinates[2:]

        self.crop_image()
        self.get_empty_areas_on_croped(5)
        # self.det_faces()
        self.get_comp_colors()
        self.model = model

    def generate(self):
        all_results = []
        all_results.extend(patterns.gen_simple_pattern(self))
        all_results.extend(patterns.gen_simple_pattern(self, with_mask=True))
        all_results.extend(patterns.create_pattern_vacancy(self.text, self.forms_root, self.fonts_root))
        all_results.extend(patterns.create_pattern_checkmarks(self))
        all_results.extend(patterns.create_pattern_header_at_top_checkmarks(self.text, self.forms_root,
                                                                            self.fonts_root))
        all_results.extend(patterns.gen_interview_pattern(self))
        all_results.extend(patterns.gen_interview_pattern(self, pattern_type='color'))
        # all_results.extend(create_pattern_vacancy_description(self.text))
        return all_results

    def generate_image_by_image(self, israndom=False):
        generation_patterns = [partial(patterns.gen_simple_pattern, self),
                               partial(patterns.gen_simple_pattern, self, with_mask=True),
                               partial(patterns.create_pattern_vacancy, text=self.text, forms_root=self.forms_root,
                                       fonts_root=self.fonts_root),
                               partial(patterns.create_pattern_checkmarks, self),
                               partial(patterns.create_pattern_header_at_top_checkmarks, text=self.text,
                                       forms_root=self.forms_root, fonts_root=self.fonts_root),
                               partial(patterns.gen_interview_pattern, self),
                               partial(patterns.gen_interview_pattern, self, pattern_type='color')]

        for pattern in generation_patterns:
            for image in pattern():
                yield image

    def apply_all_enhance(self):
        self.original_image = self.image.copy()
        self.image = self.enhancer.apply_all(self.enhancer_factors['britness_factor'],
                                             self.enhancer_factors['contrast_factor'],
                                             self.enhancer_factors['color_factor'],
                                             self.enhancer_factors['sharpness_factor'])

    def set_enhancer_factors(self, britness_factor, contrast_factor, color_factor, sharpness_factor):
        self.enhancer_factors['britness_factor'] = britness_factor
        self.enhancer_factors['contrast_factor'] = contrast_factor
        self.enhancer_factors['color_factor'] = color_factor
        self.enhancer_factors['sharpness_factor'] = sharpness_factor

    def get_comp_colors(self, n_colors=4):
        self.comp_colors = []
        gcc = comp_colors.get_complement_colors(io.BytesIO(self.image_bytes), n_colors)
        base_colors = [(0, 170, 19), (255, 117, 0),
                       (151, 215, 0), (255, 198, 0), (224, 0, 77)]
        self.comp_colors = comp_colors.get_based_colors(base_colors, gcc)
        return self.comp_colors

    def generate_image_mask(self):
        """
        Return:
          mask of key objects
        """
        _, self.mask = segmentation.seg(self.image_bytes, self.seg_model_path)
        return self.mask

    def crop_image(self):
        self.croped_images = image_enhance.crop_by_sqare(mask=self.mask, coordinates=self.obj_coordinates,
                                                         img=self.image, scale=self.scale)
        self.croped_masks = image_enhance.crop_by_sqare(mask=self.mask, coordinates=self.obj_coordinates,
                                                        scale=self.scale)

    def get_empty_areas_on_croped(self, count):
        self.empty_areas = []
        for cr in self.croped_masks:
            self.empty_areas.append(segmentation.get_empty_areas(cr, count, self.scale))
