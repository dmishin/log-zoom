from PIL import Image
"""Utility functions for simplifying image distortions using functions"""

#Elementary transformations and operations on them
def compose( *transforms ):
    """Compose transform fucntions.
    Function must take 2 arguments x,y and return either tuple (x1,y1) or None

    tc = compose(a,b,c)

    assert tc(x,y) == a(*b(*c(x,y)))  for all x,y in domain of tc.
    """
    if not all(map(callable, transforms)):
        raise TypeError("Non-callable object passed as trnasform function")
    def composed(*xy):
        for t in reversed(transforms):
            xy = t(*xy)
            if xy is None: return None
        return xy
    return composed

def scale_tfm(k, ky=None):
    if ky is None: 
        ky = k
    def tfm(x,y):
        return x*k, y*ky
    return tfm

def translate_tfm(dx,dy):
    def tfm(x,y):
        return x+dx, y+dy
    return tfm

def memoize_tfm( tfm, dictionary=None, memo_size=1024 ):
    """Does not makes a big deal"""
    queue = deque()
    dictionary = dict() if (dictionary is None) else dictionary
    def memoized( *xy ):
        try:
            return dictionary[xy]
        except KeyError:
            dictionary[xy] = f = tfm(*xy)
            queue.append(xy)
            if len(queue) > memo_size:
                del dictionary[queue.popleft()]
            return f
    return memoized



def transform_image(source, tfm_func, out_size, mesh_step, add_alpha=False):
    """Transforms image using given distortion function.
    The function must fromsform target image coordinates to source image coordinates"""
    out_width, out_height = out_size
    mesh = make_mesh(tfm_func, out_width, out_height, mesh_step)
    if add_alpha:
        mesh = list(mesh)
    out = source.transform(out_size, Image.MESH, 
                           mesh, 
                           Image.BICUBIC )

    if add_alpha:
        alpha = Image.new("L", im.size, 255).transform(
            out_size, Image.MESH, 
            mesh,
            Image.NEAREST )
        out.putalpha(alpha)
    return out

def make_mesh_simple(tfm_func, out_width, out_height, mesh_step):
    """Generates mesh data, accepted by the Image.transform, for the given geometry transformation function"""
    for yd in range(0,out_height,mesh_step):
        for xd in range(0,out_width, mesh_step):
            #suboptimal... but fast enough for me. Possible optimization: remember map function values.
            box = (xd,yd,xd+mesh_step,yd+mesh_step)
            quad = eval_box_corners(box)
            yield( (box,quad) )


def eval_box_corners(box, tfm_func):
    """" (x1,x1,y1,y2) -> ( xa, ya, xb, yb, xc, yc, xd, yd )
      ad
      bc
    """
    x1,y1,x2,y2 = box
    return tfm_func(x1,y1) + tfm_func(x1,y2) + tfm_func(x2,y2) + tfm_func(x2,y1)

def make_mesh_for_domain(tfm_func, out_width, out_height, mesh_step, 
                         treat_disconts=True, discontinuous_limit=100):
    """Create mesh for a function, defined on a domain.
    Function is expected to return None if there is no value
    """
    def continuous(a,b,c,d):
        xx = a[0],b[0],c[0],d[0]
        yy = a[1],b[1],c[1],d[1]
        return max(xx) - min(xx) < discontinuous_limit and max(yy)-min(yy) < discontinuous_limit

    def subdivisions(box):
        # A D
        # B C
        x1,y1,x2,y2 = box
        w = x2-x1
        h = y2-y1
        if not w or not h: return
        
        a = tfm_func(x1,y1)
        b = tfm_func(x1,y2)
        c = tfm_func(x2,y2)
        d = tfm_func(x2,y1)

        if not (a or b or c or d): return

        is_big = w>1 or h>1
        
        if a and b and c and d:
            #Function is fully defined in the corners (Assume true for the whole block)
            if treat_disconts:
                if continuous(a,b,c,d):
                    yield (box, a+b+c+d)
                    return
                #not continuous
                if not is_big:
                    yield (box, a+a+a+a)
                    return
                #else - pass to the subdivisions
            else:
                yield (box, a+b+c+d)
                return

        if is_big:
            xm = x1 + w//2
            ym = y1 + h//2
            yield from subdivisions( (x1, y1, xm, ym) )
            yield from subdivisions( (xm, y1, x2, ym) )
            yield from subdivisions( (x1, ym, xm, y2) )
            yield from subdivisions( (xm, ym, x2, y2) )
    ############### End of generator ##########################
    #Top-level grid
    for yd in range(0,out_height,mesh_step):
        for xd in range(0,out_width, mesh_step):
            #suboptimal... but fast enough for me. Possible optimization: remember map function values.
            yield from subdivisions((xd,yd,xd+mesh_step,yd+mesh_step))
    
"""
def make_mesh_adaptive(tfm_func, out_width, out_height, min_absolute_distortion=None):
    if min_absolute_distortion is None:
        min_absolute_distortion = max(1, min( 5, (out_width+out_height)*0.05 ))
    min_absolute_distortion2 = .1 #min_absolute_distortion ** 2

    def subdivide_quad(box, quad):
        x1,y1,x2,y2 = box
        if min(x2-x1, y2-y1) <= 1: 
            yield ( (box, quad) )
        else:
            w = x2-x1
            h = y2-y1
            w2 = w // 2
            h2 = h // 2
            #New point is not exactly at the center - get the proportion.
            px = w2 / w #around 0.5
            py = h2 / h
            qx = 1-px
            qy = 1-py
            assert( px > 0.4 and px < 0.6 )

            #_Approximate_ center of the box
            box_center = (x1+w2, y1+h2) 

            #Calculate linear approximation to quad center
            xa,ya,xb,yb,xc,yc,xd,yd = quad
            # ad
            # bc
            qc_x_linapprox = (xa*qx + xd*px)*qy + (xb*qx + xc*px)*py;
            qc_y_linapprox = (ya*qx + yd*px)*qy + (yb*qx + yc*px)*py;
            
            #And now compare it with the value, the function returns
            qc_x, qc_y = f_center = tfm_func( *box_center )
            
            #Get the distance
            dist2 = (qc_x - qc_x_linapprox)**2 + (qc_y - qc_y_linapprox)**2
            sz2 = (xa-xc)**2 + (ya-yc)**2 + (xd-xb)**2 + (yd-yb)**2
            
            if dist2 < sz2 * 0.00001:
                #No need to subdivide
                #print ("#### no subdiv, yield: ", box, quad )
                yield ( (x1,y1,x2-1,y2-1), quad)
            else:
                #Subdivision required
                xx = (x1, x1+w2, x2)
                yy = (y1, y1+h2, y2)
                #TODO: 5 of 9 are already calculated!
                ff = [[tfm_func(xi,yi) for xi in xx] for yi in yy]
                for i in (0,1):
                    for j in (0,1):
                        box = (xx[i], yy[j], xx[i+1], yy[j+1])
                        quad = ff[j][i] + ff[j+1][j] + ff[j+1][i+1] + ff[j][i+1]
                        #print ("#### sub-box", box, "sub-quad", quad)
                        yield from subdivide_quad( box, quad )
    
    box = (0,0,out_width, out_height)
    quad = eval_box_corners(box, tfm_func)
    yield from subdivide_quad( box, quad )

"""
make_mesh = make_mesh_for_domain
