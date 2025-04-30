from geometry import Point, Triangle, Edge, EPSILON
import math

class VoronoiDiagram:
    """Класс для построения диаграммы Вороного на основе триангуляции Делоне."""

    def __init__(self, delaunay_triangles: list[Triangle], canvas_bounds):
        """
        Инициализация.
        :param delaunay_triangles: Список треугольников Делоне.
        :param canvas_bounds: Кортеж (min_x, min_y, max_x, max_y) границ холста для обрезки лучей.
        """
        self.triangles = delaunay_triangles
        self.edges: list[tuple[Point, Point] | tuple[Point, Point, Point]] = []
        self.vertices: dict[Triangle, Point] = {}
        self.canvas_bounds = canvas_bounds

    def compute(self):
        """Вычисляет ребра диаграммы Вороного."""
        self.edges.clear()
        self.vertices.clear()

        if not self.triangles:
            return


        for triangle in self.triangles:
            center, radius_sq = triangle.circumcenter_radius_sq
            if radius_sq != float('inf'):
                self.vertices[triangle] = center


        edge_to_triangles: dict[Edge, list[Triangle]] = {}
        for triangle in self.triangles:
            for edge in triangle.edges:
                if edge not in edge_to_triangles:
                    edge_to_triangles[edge] = []
                edge_to_triangles[edge].append(triangle)


        for edge, triangles in edge_to_triangles.items():
            if len(triangles) == 2:

                t1, t2 = triangles
                if t1 in self.vertices and t2 in self.vertices:
                    v1 = self.vertices[t1]
                    v2 = self.vertices[t2]
                    if v1 != v2 :
                         self.edges.append((v1, v2))
            elif len(triangles) == 1:

                t1 = triangles[0]
                if t1 in self.vertices:
                    v1 = self.vertices[t1]
                    p1, p2 = edge.p1, edge.p2


                    edge_vec_x = p2.x - p1.x
                    edge_vec_y = p2.y - p1.y


                    mid_x = (p1.x + p2.x) / 2.0
                    mid_y = (p1.y + p2.y) / 2.0



                    norm_vec_x = -edge_vec_y
                    norm_vec_y = edge_vec_x



                    other_vertex = None
                    for v in t1.vertices:
                        if v != p1 and v != p2:
                            other_vertex = v
                            break


                    to_other_x = other_vertex.x - mid_x
                    to_other_y = other_vertex.y - mid_y




                    dot_product = norm_vec_x * to_other_x + norm_vec_y * to_other_y

                    if dot_product > 0:
                        norm_vec_x *= -1
                        norm_vec_y *= -1


                    length = math.sqrt(norm_vec_x**2 + norm_vec_y**2)
                    if length > EPSILON:
                        dir_x = norm_vec_x / length
                        dir_y = norm_vec_y / length
                    else:
                        dir_x, dir_y = 0, 0


                    end_point = self._clip_ray(v1, Point(v1.x + dir_x, v1.y + dir_y))
                    if end_point:


                         self.edges.append((v1, end_point))


        return self.edges

    def _clip_ray(self, start_point: Point, point_on_ray: Point) -> Point | None:
        """Обрезает луч границами холста."""
        min_x, min_y, max_x, max_y = self.canvas_bounds
        sx, sy = start_point.x, start_point.y
        dx = point_on_ray.x - sx
        dy = point_on_ray.y - sy

        t_min = 0.0
        t_max = float('inf')


        if abs(dx) < EPSILON:

            if sx < min_x or sx > max_x:
                return None
        else:
            t1 = (min_x - sx) / dx
            t2 = (max_x - sx) / dx
            if t1 > t2: t1, t2 = t2, t1
            t_min = max(t_min, t1)
            t_max = min(t_max, t2)


        if abs(dy) < EPSILON:

            if sy < min_y or sy > max_y:
                return None
        else:
            t1 = (min_y - sy) / dy
            t2 = (max_y - sy) / dy
            if t1 > t2: t1, t2 = t2, t1
            t_min = max(t_min, t1)
            t_max = min(t_max, t2)


        if t_min < t_max and t_max > EPSILON:
            intersection_t = -1.0


            if dx != 0:
                t = (min_x - sx) / dx
                if t >= -EPSILON:
                    py = sy + t * dy
                    if min_y - EPSILON <= py <= max_y + EPSILON:
                         if intersection_t < 0 or t < intersection_t: intersection_t = t


            if dx != 0:
                t = (max_x - sx) / dx
                if t >= -EPSILON:
                    py = sy + t * dy
                    if min_y - EPSILON <= py <= max_y + EPSILON:
                         if intersection_t < 0 or t < intersection_t: intersection_t = t


            if dy != 0:
                t = (min_y - sy) / dy
                if t >= -EPSILON:
                    px = sx + t * dx
                    if min_x - EPSILON <= px <= max_x + EPSILON:
                        if intersection_t < 0 or t < intersection_t: intersection_t = t


            if dy != 0:
                t = (max_y - sy) / dy
                if t >= -EPSILON:
                    px = sx + t * dx
                    if min_x - EPSILON <= px <= max_x + EPSILON:
                        if intersection_t < 0 or t < intersection_t: intersection_t = t

            draw_len = max(max_x - min_x, max_y - min_y) * 2
            end_x = sx + dx * draw_len
            end_y = sy + dy * draw_len
            return Point(end_x, end_y)

        return None