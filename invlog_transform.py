#!/usr/bin/env python
from PIL import Image
from math import *
import os
from image_distort import transform_image, compose, scale_tfm, translate_tfm

def inv_logpolar_transform(image_size, y0, out_width, out_height, alpha0 = 0):
    """Inverse log polar transform
    """
    xc = out_width/2
    yc = out_height/2
    center = (xc,yc)
    

    swidth, sheight = image_size

    log_rmax = log(xc**2+yc**2)*0.5
    
    #source image scale (pixels per unit)
    # image width must be 2PI units
    source_scale = (swidth-1)/2/pi
    
    
    
    def logz(xf,yf):
        if xf == 0 and yf == 0:
            return 0, 1e-2
        else:
            return atan2(yf, xf), log(xf*xf+yf*yf)*0.5

        
    tfm_func1 = compose(
        #without translate, min y is: -log_rmax*source_scale. It must be y0.
        translate_tfm( source_scale*pi, log_rmax*source_scale+y0 ),
        scale_tfm( source_scale, -source_scale ),
        logz,
        translate_tfm(-xc, -yc)
    )

    return tfm_func1

def main():
    from optparse import OptionParser
    parser = OptionParser(usage = "%prog [options] INPUT_IMAGE OUTPUT_IMAGE\n"
                          "Log-Polar image transform. Generated image always have RGBA format")

    parser.add_option("-t", "--top", dest="top", type=int, default=0,
                      help="Position of the top line in the source image to use", metavar="Y")

    parser.add_option("-w", "--width", dest="width", type=int, default=1024,
                      help="Width of the output image", metavar="PIXELS")

    parser.add_option("-H", "--height", dest="height", type=int, default=1024,
                      help="Height of the output image", metavar="PIXELS")

    parser.add_option("", "--mesh-step", dest="mesh_step", type=int, default=8,
                      help="Step of the output mesh. Default is 8", metavar="PIXELS")

    (options, args) = parser.parse_args()
    
    if len(args) < 1:
        parser.error("No input file specified")

    input =args[0]
    if len(args) >= 2:
        output = args[1]
    else:
        output = None

    img = Image.open(input)

    #Image conversions
    #  SOurce image can be one of:
    #    - RGB
    #    - RGBA  - has alpha
    #    - I     - may have alpha
    #    - L
    #    - 1

    # Target image:
    #   always have alpha.
    
    if img.mode != "RGBA":
        img =img.convert("RGBA")

    out_size = (options.width, options.height)
    transform = inv_logpolar_transform(img.size,
                                       options.top, 
                                       options.width,
                                       options.height)

    img = transform_image(img, transform, out_size, mesh_step=options.mesh_step)

    if output:
        img.save(output)
    else:
        img.show()
    

if __name__=="__main__":
    main()
