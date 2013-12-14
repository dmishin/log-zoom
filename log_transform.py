#!/usr/bin/env python
from PIL import Image
from math import *
import os
from image_distort import transform_image, compose, scale_tfm, translate_tfm

def logpolar_transform(image_size, center, out_width=None, out_height=None, alpha0 = 0):
    swidth, sheight = image_size
    if center is None:
        center = (swidth/2, sheight/2)

    if out_width is None:
        #Automatically determine output width
        #Should be enough for mostly loseless transform
        out_width = (swidth+sheight)*2

    x0,y0 = center

    min_log = log(0.5)
    max_log = log(max(x0, swidth-x0)**2 + max(y0,sheight-y0)**2)*0.5

    #Determine appropriate height of the output image, requiring that whole original
    # image fits into it, and highest zoom levels is single pixel.
    if out_height is None:
        out_height = int(out_width / (2*pi) * (max_log-min_log))
    out_size = (out_width, out_height)
    out_scale = 2*pi/out_width


    def expz(xf,yf):
        ey = exp(yf)
        return cos(xf)*ey, sin(xf)*ey

    tfm_func1 = compose(
        translate_tfm(x0, y0),
        expz,
        translate_tfm( alpha0, max_log ),
        scale_tfm( out_scale, -out_scale)
    )

    def tfm_func(x,y):
        xf = x*out_scale + alpha0
        yf = max_log-y*out_scale #Put highest resolution at the top
        ey = exp(yf)
        yfs = sin(xf)*ey
        xfs = cos(xf)*ey
        return xfs + x0, yfs + y0

    return (out_width, out_height), tfm_func

def main():
    from optparse import OptionParser
    parser = OptionParser(usage = "%prog [options] INPUT_IMAGE OUTPUT_IMAGE\n"
                          "Log-Polar image transform. Generated image always have RGBA format")

    parser.add_option("-c", "--center", dest="center",
                      help="Center point position, x:y", metavar="X:Y")

    parser.add_option("-A", "--angle", dest="angle", type=float, default=0.0,
                      help="Angle, corresponding left side of the transformed image, in graduses. 0 is horizontal, left to right.", metavar="ANGLE")

    parser.add_option("-w", "--width", dest="width", type=int,
                      help="Width of the output image. Default is auto-detect, based on the source inmage dimensions (the size is usually quite big)", metavar="PIXELS")

    parser.add_option("-H", "--height", dest="height", type=int,
                      help="Height of the output image. Default is auto-detect, based on width", metavar="PIXELS")

    parser.add_option("", "--mesh-step", dest="mesh_step", type=int, default=8,
                      help="Step of the output mesh. Default is 8", metavar="PIXELS")

    parser.add_option("", "--mercator2ortho", dest="mercator2ortho",
                      help="Treat source image as a piece of the map in Mercator projection. Map in converted to orthogonal projection regarding the point in the center of the map.", metavar="CENTER_LAT:LNG_WIDTH")

    (options, args) = parser.parse_args()
    
    if len(args) < 1:
        parser.error("No input file specified")

    input =args[0]
    if len(args) >= 2:
        output = args[1]
    else:
        output = None

    if options.mercator2ortho:
        if options.center:
            parser.error("Center not supported in mercator map pieces. It is always at the center of the image")
            
        try:
            lat_center_s, lng_extent_s = options.mercator2ortho.split(":",2)
            mercator2ortho_options = {
                "center_lat": float(lat_center_s)/180*pi,
                "lng_extent": float(lng_extent_s)/180*pi
            }
        except Exception as err:
            parser.error("Error parsing mercator projection options: {0}".format(err))
    else:
        mercator2ortho_options = None

    if options.center is None:
        center = None
    else:
        center = tuple(map(int, options.center.split(":",2)))

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

    if mercator2ortho_options:
        from mercator2ortho import mercator2ortho
        out_ortho_size, merc2otrho_tfm, _ = mercator2ortho(img.size,
                                                        mercator2ortho_options["center_lat"], 
                                                        mercator2ortho_options["lng_extent"], 
                                                        max(img.size)
                                                    )

        out_size, ortho2log_tfm = logpolar_transform(out_ortho_size,
                                                     center=scale_tfm(0.5)(*out_ortho_size), 
                                                     out_width = options.width,
                                                     alpha0 = options.angle/180*pi)
        #Create composite transform: first convert Mercator map to orthogonal projection, then apply log-transform to it.
        transform = compose(
            merc2otrho_tfm,
            ortho2log_tfm )

    else:
        out_size, transform = logpolar_transform(img.size,
                                                 center=center, 
                                                 out_width = options.width,
                                                 alpha0 = options.angle/180*pi)

    img = transform_image(img, transform, out_size, mesh_step=options.mesh_step)

    if output:
        img.save(output)
    else:
        img.show()
    

if __name__=="__main__":
    main()
