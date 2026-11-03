from PIL import Image, ImageDraw, ImageOps

from bot.data.sticker import STICKER_SIZE


class FrameShaper:
    @classmethod
    def shape(cls, img: Image.Image, sticker_type: str, working_size: int) -> Image.Image:
        match sticker_type:
            case 'crop':
                img = ImageOps.fit(img, STICKER_SIZE)
            case 'circle':
                img = cls._apply_circle_mask(img)
            case 'rounded':
                img = cls._apply_rounded_mask(img)
            case _:  # full
                img = cls._contain_on_transparent(img)
        if working_size < STICKER_SIZE[0]:
            img = cls._pixelate(img, working_size)
        return img

    @classmethod
    def _pixelate(cls, img: Image.Image, working_size: int) -> Image.Image:
        small = img.resize((working_size, working_size), Image.Resampling.BILINEAR)
        return small.resize(STICKER_SIZE, Image.Resampling.NEAREST)

    @classmethod
    def _contain_on_transparent(cls, img: Image.Image) -> Image.Image:
        img = ImageOps.contain(img, STICKER_SIZE)
        canvas = Image.new('RGBA', STICKER_SIZE, (0, 0, 0, 0))
        x = (STICKER_SIZE[0] - img.width) // 2
        y = (STICKER_SIZE[1] - img.height) // 2
        canvas.paste(img, (x, y), img)
        return canvas

    @classmethod
    def _apply_circle_mask(cls, img: Image.Image) -> Image.Image:
        img = ImageOps.fit(img, STICKER_SIZE)
        mask = Image.new('L', STICKER_SIZE, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, *STICKER_SIZE), fill=255)
        canvas = Image.new('RGBA', STICKER_SIZE, (0, 0, 0, 0))
        canvas.paste(img, mask=mask)
        return canvas

    @classmethod
    def _apply_rounded_mask(cls, img: Image.Image) -> Image.Image:
        img = ImageOps.fit(img, STICKER_SIZE)
        radius = STICKER_SIZE[0] // 8
        mask = Image.new('L', STICKER_SIZE, 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle((0, 0, *STICKER_SIZE), radius=radius, fill=255)
        canvas = Image.new('RGBA', STICKER_SIZE, (0, 0, 0, 0))
        canvas.paste(img, mask=mask)
        return canvas
