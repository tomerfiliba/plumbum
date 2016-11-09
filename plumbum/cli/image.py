from __future__ import print_function, division

from plumbum import colors
from plumbum.cli.termsize import get_terminal_size
from plumbum import cli
import sys

def show_image(filename, size=None, double=False):
    """Display an image on the command line. Can select a size or show in double resolution."""
    from PIL import Image
    if double:
        return show_image_pil_double(Image.open(filename), size)
    else:
        return show_image_pil(Image.open(filename), size)

def show_image_pil(im, size=None):
    'Standard show routine'
    term_size = get_terminal_size()
    if size is None:
        size = term_size

    new_im = im.resize(size)

    for y in range(size[1]):
        for x in range(size[0]):
            pix = new_im.getpixel((x,y))
            print(colors.bg.rgb(*pix), ' ', sep='', end='') # u'\u2588'
        print()
    print(colors.reset)

def show_image_pil_double(im, size=None):
    'Show double resolution on some fonts'
    term_size = get_terminal_size()
    if size is None:
        size = term_size

    size= (size[0], size[1]*2)

    new_im = im.resize(size)

    for y in range(size[1]//2):
        for x in range(size[0]):
            pix = new_im.getpixel((x,y*2))
            pixl = new_im.getpixel((x,y*2+1))
            print(colors.bg.rgb(*pixl) & colors.fg.rgb(*pix), '\u2580', sep='', end='')
        print()
    print(colors.reset)

class ShowImage(cli.Application):
    'Display an image on the terminal'
    double = cli.Flag(['-d','--double'], help="Double resolution (only looks good with some fonts)")

    @cli.switch(['-c','--colors'], cli.Range(1,4), help="Level of color, 1-4")
    def colors_set(self, n):
        colors.use_color = n

    size = cli.SwitchAttr(['-s','--size'], help="Size, should be in the form 100x150")
    @cli.positional(cli.ExistingFile)
    def main(self, filename):

        size=None
        if self.size:
            size = map(int, self.size.split('x'))

        show_image(filename, size, self.double)

if __name__ == '__main__':
    ShowImage()
