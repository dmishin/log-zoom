#!/usr/bin/env python
from os.path import splitext
from urllib.request import urlopen
import shutil
#     Use google static api
#     Explanations: https://developers.google.com/maps/documentation/staticmaps/index
#     http://maps.googleapis.com/maps/api/staticmap?center=-15.800513,-47.91378&zoom=13&size=800x800&sensor=false

#from enum import Enum

__map_types={ "satellite", "roadmap", "hybrid", "terrain"}

__ext2format={".png": "png",
              ".jpg": "jpg",
              ".jpeg": "jpg",
              ".gif": "gif"}

def get_map_stream( center, zoom, size, type, format, scale=1 ):
    if format is None: raise ValueError("Format not specified")
    w,h = size
    if max(w,h) >640:
        print("Warning: requested map size is too big, it will probably be truncated", file=sys.stderr)
    args = {"longitude": center[1],
            "lattitude": center[0],
            "zoom": zoom,
            "width": w,
            "height": h,
            "type": str(type),
            "format": format,
            "scale":scale}
    url = "http://maps.googleapis.com/maps/api/staticmap?"\
          "center={lattitude:0.10f},{longitude:0.10f}&"\
          "zoom={zoom:d}&size={width:d}x{height:d}&scale={scale:d}&"\
          "maptype={type:s}&sensor=false&format={format:s}".format(**args)
    return urlopen( url )

def is_supported_map_type(type):
    return type in __map_types

def get_map(outfile, center, zoom, size, type="satellite", format=None, scale=1):
    if not is_supported_map_type(type): raise ValueError("Bad map type: {0}".format(type))
    if isinstance(outfile, str):
        ext = splitext(outfile)[1]
        if format is None:
            format = __ext2format[ext.lower()]
        with open(outfile,"wb") as hfile:
            return get_map(hfile, center, zoom, size, type, format=format)

    stream = get_map_stream( center, zoom, size, type, format, scale )
    try:
        shutil.copyfileobj(stream, outfile)
    finally:
        stream.close()


def main():
    from optparse import OptionParser
    parser = OptionParser(usage = "%prog [options] LATTITUDE LONGITUDE ZOOM OUTPUT\n"
                          "Download static google map around given point.\n"
                          "  ZOOM is numberic zoom level, from 0 (whole world) to 18..19. At zoom level 0, whole map has size 256x256 pixels.\n"
                          "  Size of the image is limited by Google, 640x640 is maximum. Greater sizes (up to 640*2) are requested using 'scale' feature.")

    parser.add_option("-s", "--size", dest="size", default="512:512",
                      help="Image size", metavar="WIDTH:HEIGHT")

    parser.add_option("-S", "--scale", dest="scale", type=int, default=1,
                      help="Map scale, 1 or 2", metavar="1_OR_2")

    parser.add_option("-t", "--type", dest="type", default="satellite",
                      metavar="MAP_TYPE",
                      help="Type of the map. Can be one of Satellite/Roadmap/Terrain/Composite")

    (options, args) = parser.parse_args()
    
    if len(args) != 4:
        parser.error("Must have 4 arguments")
    if options.scale not in (1,2):
        parser.error("Wrong scale: {0}".format(options.scale))
    size = tuple(map(int, options.size.split(":",2)))
    slattitude, slongitude, szoom, output = args
    try:
        longitude = float(slongitude)
        lattitude = float(slattitude)
        zoom = int(szoom)
    except Exception as e:
        parser.error("Faield to parse argument: %s"%(e))

    get_map( output, (lattitude, longitude), zoom, size, type=options.type.lower() )

if __name__=="__main__": main()
