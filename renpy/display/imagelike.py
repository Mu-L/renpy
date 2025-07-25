# Copyright 2004-2025 Tom Rothamel <pytom@bishoujo.us>
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# This file contains displayables that are image-like, because they take
# up a rectangular area of the screen, and do not respond to input.

from __future__ import division, absolute_import, with_statement, print_function, unicode_literals
from renpy.compat import PY2, basestring, bchr, bord, chr, open, pystr, range, round, str, tobytes, unicode  # *


import renpy
from renpy.display.render import render, Render
from renpy.display.matrix import Matrix2D


class Solid(renpy.display.displayable.Displayable):
    """
    :doc: disp_imagelike

    A displayable that fills the area its assigned with `color`.

    ::

        image white = Solid("#fff")

    """

    def __init__(self, color, **properties):
        super(Solid, self).__init__(**properties)

        if color is not None:
            self.color = renpy.easy.color(color)
        else:
            self.color = None

    def __hash__(self):
        return hash(self.color)

    def __eq__(self, o):
        if not self._equals(o):
            return False

        return self.color == o.color

    def visit(self):
        return []

    def render(self, width, height, st, at):
        xminimum, yminimum = renpy.display.layout.xyminimums(self.style, width, height)

        width = max(xminimum, width)
        height = max(yminimum, height)

        color = self.color or self.style.color

        rv = Render(width, height)

        if width and height:
            minw, minh = renpy.display.draw.draw_to_virt.transform(1, 1)

            width = max(width, minw)
            height = max(height, minh)

        if color is None or width <= 0 or height <= 0:
            return rv

        SIZE = 10

        if width < SIZE or height < SIZE:
            tex = renpy.display.draw.solid_texture(width, height, color)
        else:
            tex = renpy.display.draw.solid_texture(SIZE, SIZE, color)
            rv.forward = Matrix2D(1.0 * SIZE / width, 0, 0, 1.0 * SIZE / height)
            rv.reverse = Matrix2D(1.0 * width / SIZE, 0, 0, 1.0 * height / SIZE)

        rv.blit(tex, (0, 0))

        return rv


class Borders(object):
    """
    :doc: disp_imagelike

    This object provides border size and tiling information to a :func:`Frame`.
    It can also provide padding information that can be supplied to the
    :propref:`padding` style property of a window or frame.

    `left`, `top`, `right`, `bottom`
        These provide the size of the insets used by a frame, and are added
        to the padding on each side. They should be zero or a positive integer.

    `pad_left`, `pad_top`, `pad_right`, `pad_bottom`
        These are added to the padding on each side, and may be positive or
        negative. (For example, if `left` is 5 and `pad_left` is -3, the final
        padding is 2.)

    The padding information is supplied via a field:

    .. attribute:: padding

        This is a four-element tuple containing the padding on each of the
        four sides.
    """

    def __init__(self, left, top, right, bottom, pad_left=0, pad_top=0, pad_right=0, pad_bottom=0):
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom

        self.pad_left = pad_left
        self.pad_top = pad_top
        self.pad_right = pad_right
        self.pad_bottom = pad_bottom

    @property
    def padding(self):
        return (
            self.left + self.pad_left,
            self.top + self.pad_top,
            self.right + self.pad_right,
            self.bottom + self.pad_bottom,
        )


class Frame(renpy.display.displayable.Displayable):
    """
    :doc: disp_imagelike
    :args: (image, left=0, top=0, right=None, bottom=None, *, tile=False, **properties)
    :name: Frame

    A displayable that resizes an image to fill the available area,
    while preserving the width and height of its borders. It is often
    used as the background of a window or button.

    .. figure:: frame_example.png

        Using a frame to resize an image to double its size.

    `image`
        An image manipulator that will be resized by this frame.

    `left`
        The size of the border on the left side. This can also be a
        :func:`Borders` object, in which case that object is used in place
        of the other parameters.

    `top`
        The size of the border on the top.

    `right`
        The size of the border on the right side. If None, defaults
        to `left`.

    `bottom`
        The side of the border on the bottom. If None, defaults to `top`.

    `tile`
        If set to True, tiling is used to resize sections of the image,
        rather than scaling. If set to the string "integer", the nearest
        integer number of tiles will be used in each direction. That set of
        full tiles will then be scaled up or down to fit the required area.

    ::

         # Resize the background of the text window if it's too small.
         init python:
             style.window.background = Frame("frame.png", 10, 10)
    """

    __version__ = 1

    properties = {}
    tile_ratio = 0.5

    def after_upgrade(self, version):
        if version < 2:
            self.left = self.xborder  # type: ignore
            self.right = self.xborder  # type: ignore
            self.top = self.yborder  # type: ignore
            self.bottom = self.yborder  # type: ignore

    def __init__(
        self,
        image,
        left=None,
        top=None,
        right=None,
        bottom=None,
        xborder=0,
        yborder=0,
        bilinear=True,
        tile=False,
        tile_ratio=0.5,
        **properties,
    ):
        super(Frame, self).__init__(**properties)

        self.image = renpy.easy.displayable(image)
        self._duplicatable = self.image._duplicatable

        if isinstance(left, Borders):
            insets = left

            left = insets.left
            top = insets.top
            right = insets.right
            bottom = insets.bottom

        self.tile = tile
        # When tile="integer" the proportion of an edge tile that determines
        # whether to use less tiles and stretch or more tiles and shrink
        self.tile_ratio = float(tile_ratio)

        # Compat for old argument names.
        if left is None:
            left = xborder
        if top is None:
            top = yborder

        if right is None:
            right = left
        if bottom is None:
            bottom = top

        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom

    def __repr__(self):
        return "<Frame {!r} ({},{},{},{}){}>".format(
            self.image,
            self.left,
            self.top,
            self.right,
            self.bottom,
            (" tile ({})".format(self.tile_ratio) if self.tile == "integer" else " tile" if self.tile else ""),
        )

    def __eq__(self, o):
        if not self._equals(o):
            return False

        if self.image != o.image:
            return False

        if self.left != o.left:
            return False
        if self.top != o.top:
            return False
        if self.right != o.right:
            return False
        if self.bottom != o.bottom:
            return False

        if self.tile != o.tile:
            return False

        if self.tile_ratio != o.tile_ratio:
            return False

        return True

    def render(self, width, height, st, at):
        width = max(self.style.xminimum, width)
        height = max(self.style.yminimum, height)

        # The size of the final displayable.
        if self.tile:
            dw = int(width)
            dh = int(height)
        else:
            dw = width
            dh = height

        if width and height:
            minw, minh = renpy.display.draw.draw_to_virt.transform(1, 1)

            width = max(width, minw)
            height = max(height, minh)

        image = self.style.child or self.image
        crend = render(image, width, height, st, at)

        sw, sh = crend.get_size()
        sw = int(sw)
        sh = int(sh)

        bw = self.left + self.right
        bh = self.top + self.bottom

        xborder = min(bw, sw - 2, dw)
        if xborder and bw:
            left = self.left * xborder // bw
            right = self.right * xborder // bw
        else:
            left = 0
            right = 0

        yborder = min(bh, sh - 2, dh)
        if yborder and bh:
            top = self.top * yborder // bh
            bottom = self.bottom * yborder // bh
        else:
            top = 0
            bottom = 0

        if renpy.display.draw.info["renderer"] == "sw":
            return self.sw_render(crend, dw, dh, left, top, right, bottom)

        def draw(x0, x1, y0, y1):
            # Compute the coordinates of the left, right, top, and
            # bottom sides of the region, for both the source and
            # destination surfaces.

            # left side.
            if x0 >= 0:
                dx0 = x0
                sx0 = x0
            else:
                dx0 = dw + x0
                sx0 = sw + x0

            # right side.
            if x1 > 0:
                dx1 = x1
                sx1 = x1
            else:
                dx1 = dw + x1
                sx1 = sw + x1

            # top side.
            if y0 >= 0:
                dy0 = y0
                sy0 = y0
            else:
                dy0 = dh + y0
                sy0 = sh + y0

            # bottom side
            if y1 > 0:
                dy1 = y1
                sy1 = y1
            else:
                dy1 = dh + y1
                sy1 = sh + y1

            # Quick exit.
            if sx0 == sx1 or sy0 == sy1:
                return

            # Compute sizes.
            csw = sx1 - sx0
            csh = sy1 - sy0
            cdw = dx1 - dx0
            cdh = dy1 - dy0

            if csw <= 0 or csh <= 0 or cdh <= 0 or cdw <= 0:
                return

            # Get a subsurface.
            cr = crend.subsurface((sx0, sy0, csw, csh))

            # Scale or tile if we have to.
            if csw != cdw or csh != cdh:
                if self.tile:
                    ctw, cth = cdw, cdh

                    xtiles = max(1, cdw // csw + (1 if cdw % csw else 0))
                    ytiles = max(1, cdh // csh + (1 if cdh % csh else 0))

                    if cdw % csw or cdh % csh:
                        # Area is not an exact integer number of tiles

                        if self.tile == "integer":
                            if cdw % csw / float(csw) < self.tile_ratio:
                                xtiles = max(1, xtiles - 1)
                            if cdh % csh / float(csh) < self.tile_ratio:
                                ytiles = max(1, ytiles - 1)

                            # Set size of the used tiles (ready to scale)
                            ctw, cth = csw * xtiles, csh * ytiles

                    newcr = Render(ctw, cth)
                    newcr.xclipping = True
                    newcr.yclipping = True

                    for x in range(0, xtiles):
                        for y in range(0, ytiles):
                            newcr.blit(cr, (x * csw, y * csh))

                    csw, csh = ctw, cth
                    cr = newcr

                if csw != cdw or csh != cdh:
                    # Subsurface needs scaling
                    newcr = Render(cdw, cdh)
                    newcr.forward = Matrix2D(1.0 * csw / cdw, 0, 0, 1.0 * csh / cdh)
                    newcr.reverse = Matrix2D(1.0 * cdw / csw, 0, 0, 1.0 * cdh / csh)
                    newcr.blit(cr, (0, 0))

                    cr = newcr

            # Blit.
            rv.blit(cr, (dx0, dy0))
            return

        rv = Render(dw, dh)
        rv.add_property("pixel_perfect", False)

        self.draw_pattern(draw, left, top, right, bottom)

        return rv

    def draw_pattern(self, draw, left, top, right, bottom):
        # Top row.
        if top:
            if left:
                draw(0, left, 0, top)

            draw(left, -right, 0, top)

            if right:
                draw(-right, 0, 0, top)

        # Middle row.
        if left:
            draw(0, left, top, -bottom)

        draw(left, -right, top, -bottom)

        if right:
            draw(-right, 0, top, -bottom)

        # Bottom row.
        if bottom:
            if left:
                draw(0, left, -bottom, 0)

            draw(left, -right, -bottom, 0)

            if right:
                draw(-right, 0, -bottom, 0)

    def sw_render(self, crend, dw, dh, left, top, right, bottom):
        source = crend.render_to_texture(True)
        sw, sh = source.get_size()

        dest = renpy.display.swdraw.surface(dw, dh, True)
        rv = dest

        def draw(x0, x1, y0, y1):
            # Compute the coordinates of the left, right, top, and
            # bottom sides of the region, for both the source and
            # destination surfaces.

            # left side.
            if x0 >= 0:
                dx0 = x0
                sx0 = x0
            else:
                dx0 = dw + x0
                sx0 = sw + x0

            # right side.
            if x1 > 0:
                dx1 = x1
                sx1 = x1
            else:
                dx1 = dw + x1
                sx1 = sw + x1

            # top side.
            if y0 >= 0:
                dy0 = y0
                sy0 = y0
            else:
                dy0 = dh + y0
                sy0 = sh + y0

            # bottom side
            if y1 > 0:
                dy1 = y1
                sy1 = y1
            else:
                dy1 = dh + y1

                sy1 = sh + y1

            # Quick exit.
            if sx0 == sx1 or sy0 == sy1 or dx1 <= dx0 or dy1 <= dy0:
                return

            # Compute sizes.
            srcsize = (sx1 - sx0, sy1 - sy0)
            dstsize = (int(dx1 - dx0), int(dy1 - dy0))

            # Get a subsurface.
            surf = source.subsurface((sx0, sy0, srcsize[0], srcsize[1]))

            # Scale or tile if we have to.
            if dstsize != srcsize:
                if self.tile:
                    tilew, tileh = srcsize
                    dstw, dsth = dstsize

                    xtiles = max(1, dstw // tilew + (1 if dstw % tilew else 0))
                    ytiles = max(1, dsth // tileh + (1 if dsth % tileh else 0))

                    if dstw % tilew or dsth % tileh:
                        # Area is not an exact integer number of tiles

                        if self.tile == "integer":
                            if dstw % tilew / float(tilew) < self.tile_ratio:
                                xtiles = max(1, xtiles - 1)
                            if dsth % tileh / float(tileh) < self.tile_ratio:
                                ytiles = max(1, ytiles - 1)

                    # Tile at least one tile in each direction
                    surf2 = renpy.display.pgrender.surface_unscaled((tilew * xtiles, tileh * ytiles), surf)

                    for y in range(0, ytiles):
                        for x in range(0, xtiles):
                            surf2.blit(surf, (x * tilew, y * tileh))

                    if self.tile is True:
                        # Trim the tiled surface to required size
                        surf = surf2.subsurface((0, 0, dstw, dsth))
                    else:
                        # Using integer full 'tiles' per side
                        srcsize = (tilew * xtiles, tileh * ytiles)
                        surf = surf2

                if dstsize != srcsize:
                    surf2 = renpy.display.scale.real_transform_scale(surf, dstsize)
                    surf = surf2

            # Blit.
            dest.blit(surf, (dx0, dy0))

        self.draw_pattern(draw, left, top, right, bottom)

        rrv = renpy.display.render.Render(dw, dh)
        rrv.blit(rv, (0, 0))
        rrv.depends_on(crend)

        # And, finish up.
        return rrv

    def _duplicate(self, args):
        image = self.image._duplicate(args)

        if image is self.image:
            return self

        image._unique()

        rv = self._copy(args)
        rv.image = image
        rv._duplicatable = image._duplicatable
        return rv

    def _unique(self):
        self.image._unique()
        self._duplicatable = False

    def _in_current_store(self):
        image = self.image._in_current_store()

        if image is self.image:
            return self

        rv = self._copy()
        rv.image = image
        return rv

    def visit(self):
        rv = [self.image]
        self.style._visit_frame(rv.append)
        return rv


class FileCurrentScreenshot(renpy.display.displayable.Displayable):
    """
    :doc: file_action_function

    A displayable that shows the screenshot that will be saved with the current
    file, if a screenshot has been taken when entering a menu or with
    :func:`FileTakeScreenshot`.

    If there is no current screenshot, `empty` is shown in its place. (If `empty` is
    None, it defaults to :func:`Null`.)
    """

    def __init__(self, empty=None, **properties):
        super(FileCurrentScreenshot, self).__init__(**properties)

        if empty is None:
            empty = renpy.display.layout.Null()

        self.empty = empty

    def render(self, width, height, st, at):
        ss = renpy.display.interface.screenshot_surface

        if ss is None:
            return renpy.display.render.render(self.empty, width, height, st, at)

        tex = renpy.display.draw.load_texture(ss)
        w, h = tex.get_size()

        rv = renpy.display.render.Render(w, h)
        rv.blit(tex, (0, 0))

        return rv
