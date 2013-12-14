#!/usr/bin/env python
from PIL import Image
from math import *
import os
from image_distort import transform_image, compose, scale_tfm, translate_tfm

def orthogonal_projection_width(mercator_image_size, latitude,  angular_width):
    """Determine withd (in earth radiuses) of the orthogonal projection of the given piece of the mercator map.
    """
    swidth, sheight = mercator_image_size

    y_merc0 = asinh(tan(latitude))

    #angular size of 1 pixel
    src_pixel_size = angular_width / swidth

    #Determine the size of the projected map piece, in the units where Earth radius = 1.
    #Determine the latitude span of the map
    h0 = y_merc0 - src_pixel_size * sheight * 0.5
    h1 = y_merc0 + src_pixel_size * sheight * 0.5
    lat0 = atan(sinh(h0))
    lat1 = atan(sinh(h1))
    #get the latitude closest to 0 i nthis span
    if (lat0 >=0 and lat1 <= 0) or (lat1 >=0 and lat0 <= 0):
        lowest_latitude = 0.0
    else:
        lowest_latitude = tuple(sorted((lat0,lat1), key=abs))[0] #lowest latitude by absolute value
    #width of the longitude pan
    if angular_width >= pi:
        longitude_projection_width = 2.0
    else:
        longitude_projection_width = 2*sin(angular_width/2)
    #finally, width of the projection, in Earth units
    projection_width = longitude_projection_width * cos(lowest_latitude)
    return projection_width

def mercator2ortho(mercator_image_size, latitude,  angular_width, out_width):
    phi0 = latitude #latitude and longitude of the 

    sin_phi0 = sin(phi0)
    cos_phi0 = cos(phi0)
    z0 = cos_phi0
    x0 = sin_phi0
    #y0 = 0
    #Absolute coordinate of the point on the sphere

    swidth, sheight = mercator_image_size
    out_height = int(sheight / swidth * out_width)

    y_merc0 = asinh(tan(phi0))


    def ortho2merc_tfm( xp, yp ):
        r2 = xp**2 + yp**2
        if r2 > 1: return None #Out of domain
        zp = sqrt(1 - r2)

        #XYZ are coordinates in the rotated coordinate system
        #Rotate them by phi (perpendicular to equator), in the xz plane
        x,z = zp * cos_phi0 - yp * sin_phi0, \
              zp * sin_phi0 + yp * cos_phi0
        y = xp
        #now (x, y, z) are global coordinates of the projected point on a sphere

        #Convert them back to angles...
        r_xy = sqrt(x**2 + y**2)
        #phi2 = atan2( z, r_xy )

        if r_xy == 0:
            return None
        return (atan2( y, x ),             #lambda2 
                asinh( z/r_xy ) - y_merc0) #asinh(tan(phi2))

    #angular size of 1 pixel
    src_pixel_size = angular_width / swidth

    #Determine the size of the projected map piece, in the units where Earth radius = 1.
    projection_width = orthogonal_projection_width(mercator_image_size, latitude,  angular_width)

    #
    dst_pixel_size = angular_width / out_width
    dst_pixel_size = projection_width / out_width


    scaled_ortho2merc_tfm = compose(
        translate_tfm(swidth*0.5, sheight*0.5),
        scale_tfm(-1.0/src_pixel_size),
        ortho2merc_tfm,
        scale_tfm(-dst_pixel_size),
        translate_tfm(-out_width*0.5, -out_height*0.5)
    )
        
    return (out_width, out_height), scaled_ortho2merc_tfm, dst_pixel_size

def main():
    from optparse import OptionParser
    parser = OptionParser(usage = "%prog [options] CENTER_LATITUDE MERCATOR_IMAGE LONGITUDE_WIDTH [OUTPUT_IMAGE]\n"
                          "Mercator map to orthogonal map image transform")

    parser.add_option("-w", "--width", dest="width", type=int,
                      help="Width of the output image. Default is same as input wdth in pixels", metavar="PIXELS")

    (options, args) = parser.parse_args()
    
    try:
        center_lat, input, longitude_width, *rest_args = args
        if len(rest_args)> 1: parser.error("Unexpected parameter")
        if len(rest_args)> 0:
            output = rest_args[0]
        else:
            output = None
    except ValueError:
        parser.error("Not enough arguments")

    img = Image.open(input)

    if img.mode != "RGBA":
        img =img.convert("RGBA")
    
    out_size, transform, _ = mercator2ortho(img.size,
                                            float(center_lat)/180*pi, 
                                            float(longitude_width)/180*pi, 
                                            options.width or img.size[0], 
                                        )

    img = transform_image(img, transform, out_size, mesh_step=16)
    if output:
        img.save(output)
    else:
        img.show()
    

if __name__=="__main__":
    main()

#sample 
# ./mercator2ortho.py 0 images/big-map.png 360
# py3 mercator2ortho.py 0 images\big-map.png 360
