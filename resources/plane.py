import pybullet as p
import os


class Plane:
    def __init__(self, client):
        self.client = client
        self.urdf_path = os.path.join(os.path.dirname(__file__), 'plane.urdf')
        self.body = p.loadURDF(fileName=self.urdf_path,
                               basePosition=[0, 0, 0],
                               physicsClientId=client)

    def get_bounds(self):
        try:
            aabb = p.getAABB(self.body, physicsClientId=self.client)
            min_pt, max_pt = aabb[0], aabb[1]
            xmin, xmax = float(min_pt[0]), float(max_pt[0])
            ymin, ymax = float(min_pt[1]), float(max_pt[1])
            return (xmin, xmax), (ymin, ymax)
        except Exception:
            try:
                with open(self.urdf_path, 'r') as f:
                    data = f.read()
                import re
                size_m = re.search(r'<box\s+size="([^"]+)"', data)
                origin_m = re.search(r'origin[^>]*xyz="([^"]+)"', data)
                if size_m:
                    sx, sy, _ = [float(x) for x in size_m.group(1).split()]
                else:
                    sx, sy = 20.0, 20.0
                if origin_m:
                    ox, oy, _ = [float(x) for x in origin_m.group(1).split()]
                else:
                    ox, oy = 0.0, 0.0
                minx = ox - sx / 2.0
                maxx = ox + sx / 2.0
                miny = oy - sy / 2.0
                maxy = oy + sy / 2.0
                return (minx, maxx), (miny, maxy)
            except Exception:
                return (-10.0, 10.0), (-10.0, 10.0)


