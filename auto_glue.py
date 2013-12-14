#!/usr/bin/env python
from gmap_get import get_map_stream, is_supported_map_type
from log_transform import logpolar_transform
from PIL import Image
from image_distort import transform_image, compose, scale_tfm, translate_tfm
from mercator2ortho import mercator2ortho
from math import *
import shutil
from io import BytesIO

def make_alpha(fragment_size, alpha_gradient_size, margins=(0,0,0,0)):
    """Create a monochrome image, white inside and fading to black at the sides gradually
    margins: [top bottom left right]
    """
    fwidth, fheight = fragment_size
    if margins != (0,0,0,0):
        mtop, mbottom, mleft, mright = margins
        alpha = Image.new("L", fragment_size,0)
        alpha.paste( make_alpha( (fwidth+mleft+mright, fheight+mbottom+mtop), alpha_gradient_size, (0,0,0,0)),
                     (mleft, mtop))
        return alpha
        
    alpha = Image.new("L", fragment_size,255)
    alpha_pix = alpha.load()
    s = 255/alpha_gradient_size
    for y in range(alpha_gradient_size):
        for x in range(0, fwidth):
            k = int(s*min(x,y))
            alpha_pix[x,y] = k
        for x in range(alpha_gradient_size, fwidth-alpha_gradient_size):
            alpha_pix[x,y] = k
        for x in range(fwidth-alpha_gradient_size, fwidth):
            k = int(s*min(fwidth-x,y))
            alpha_pix[x,y] = k
    for y in range(alpha_gradient_size, fheight-alpha_gradient_size):
        for x in range(0, alpha_gradient_size):
            k = int(s*x)
            alpha_pix[x,y] = k
        for x in range(fwidth-alpha_gradient_size, fwidth):
            k = int(s*(fwidth-x))
            alpha_pix[x,y] = k
    for y in range(fheight-alpha_gradient_size,fheight):
        for x in range(0, alpha_gradient_size):
            k = int(s*min(x,fheight-y))
            alpha_pix[x,y] = k
        for x in range(alpha_gradient_size, fwidth-alpha_gradient_size):
            alpha_pix[x,y] = k
        for x in range(fwidth-alpha_gradient_size, fwidth):
            k = int(s*min(fwidth-x,fheight-y))
            alpha_pix[x,y] = k
    return alpha

def download_and_glue(coordinates,
                      zoom_range=(0,19), 
                      fragment_size=(512,512), 
                      out_width = 1024, 
                      alpha_gradient_size=10, 
                      map_type="roadmap", 
                      mercator_to_ortho=True, 
                      mesh_step=8):

    #Increasing zoom by one level offsets image by this amount in the logarithmic view
    zoom_level_offset = (0.5*log(2)/pi)*out_width
    scale = 2

    fragment_size_scaled = tuple(s*scale for s in fragment_size)

    #Prepare alpha
    alpha = make_alpha(fragment_size_scaled, alpha_gradient_size, (0,20,0,0))

    z0, z1 = zoom_range
    out_height = int(zoom_level_offset * (z1-z0+2))
    print ("Output image size: {out_width}x{out_height}".format(**locals()))
    out_image = Image.new("RGBA",(out_width, out_height))
    dy_base = None
    for zoom in range(z0,z1+1):
        stream = get_map_stream(coordinates, zoom, fragment_size, map_type, "PNG", scale=scale)
        tempbuffer = BytesIO(stream.read())
        print("   Read data from internet.")
        fragment = Image.open(tempbuffer).convert("RGBA")

        if zoom != z0:
            fragment.putalpha(alpha)

        print ("Downloaded fragment, zoom={zoom}, size: {0}".format(fragment.size,**locals()))

        if not mercator_to_ortho:
            dy = (zoom-z0) * zoom_level_offset
            _, tfm = logpolar_transform(
                fragment.size, 
                scale_tfm(0.5)(*fragment.size),
                out_width=out_width)

        else:
            longitude_extent = (2*pi)*fragment.size[0]/256/scale*(0.5)**zoom
            #Make a transform from mercator to orthogonal
            out_ortho_size, merc2otrho_tfm, ortho_pix_size = mercator2ortho(
                fragment.size,
                coordinates[0]/180*pi,  #latitude
                longitude_extent, 
                out_width
            )
            _, log_tfm = logpolar_transform(
                out_ortho_size, 
                center = scale_tfm(0.5)(*out_ortho_size),
                out_width=out_width
            )

            if dy_base is None:
                dy_base = (0.5*log(ortho_pix_size)/pi)*out_width
                dy = 0
            else:
                dy = dy_base - (0.5*log(ortho_pix_size)/pi)*out_width
            tfm = compose( merc2otrho_tfm, log_tfm )


        transformed_size = (out_width, int(zoom_level_offset*3))
        
        #Put transformed image to the output
        paste_with_alpha(out_image, 
                         transform_image(fragment, tfm, transformed_size, mesh_step=mesh_step),
                         (0, int(dy)))
    return out_image

def paste_with_alpha(bg, img, offset):
    """Same as image.paste, but correctly works when source has gamma too"""
    r, g, b, a = img.split()
    transformed_rgb = Image.merge("RGB", (r, g, b))
    transformed_mask = Image.merge("L", (a,))
    bg.paste(transformed_rgb, offset, transformed_mask)
    return bg

if __name__=="__main__":

    from optparse import OptionParser
    parser = OptionParser(usage = "%prog [options] LATITUDE LONGITUDE [OUTPUT]\n"
                          "Create automatically glued, logarithmic map of a point")

    parser.add_option("-z", "--zoom-levels", dest="zoom_levels", default="0:19",
                      help="Range of zoom levels to download, full is 0:19", metavar="Z0:Z1")
    
    parser.add_option("-t", "--map-type", dest="map_type", default="satellite",
                      help="Type of the map. satellite/roadmap")
    parser.add_option("", "--alpha-gradient-size", type=int, default=10,
                      help="Size of the alpha gradient for glueing pieces")
    parser.add_option("-p", "--projection", dest="projection", default="orthogonal",
                      help="Projection type. Default is orthogonal. mercator is possible")
    parser.add_option("-w", "--width", dest="out_width", type=int, default=2048, metavar="PIXELS",
                      help="Width of the output image. Default is 2048.")
    parser.add_option("", "--mesh-step", dest="mesh_step", type=int, default=8, metavar="PIXELS",
                      help="Size of the mesh in the output image, used to interpolate distortion. Default is 8.")

    (options, args) = parser.parse_args()
    
    try:
        z0, z1 = map(int, options.zoom_levels.split(":"))
    except Exception as e:
        parser.error("Failed to parse zoom range: {0}".format(e))
    
    if len(args) < 2: parser.error("Not enough arguments")
    if len(args) >=2:
        try:
            coordinates = tuple(float(a) for a in args[:2])
        except Exception as e:
            parser.error("Failed to parse coordiantes: {0}".format(e))
    if len(args) == 3:
        output = args[2]
    else:
        output = None
    if len(args) > 3:
        parser.error("Too many arguments")

    map_type = options.map_type.lower()
    if not is_supported_map_type(map_type): parser.error("Bad map type: {0}".format(map_type))

    img = download_and_glue( coordinates, zoom_range=(z0,z1),map_type=map_type,out_width=options.out_width, mesh_step=options.mesh_step)
    if output is None:
        img.show()
    else:
        img.save(output)
        

#59.937780 30.494908

