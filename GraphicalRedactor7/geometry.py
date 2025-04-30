import math
import sys

EPSILON = sys.float_info.epsilon

class Point:
    """Класс для представления точки."""
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)

    def __eq__(self, other):
        return abs(self.x - other.x) < EPSILON and abs(self.y - other.y) < EPSILON

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):


        return hash((round(self.x / EPSILON), round(self.y / EPSILON)))

    def __str__(self):
        return f"P({self.x:.2f}, {self.y:.2f})"

    def distance_sq(self, other):
        """Возвращает квадрат расстояния до другой точки."""
        dx = self.x - other.x
        dy = self.y - other.y
        return dx*dx + dy*dy

class Edge:
    """Класс для представления ребра (отрезка)."""
    def __init__(self, p1: Point, p2: Point):

        if p1.x < p2.x or (abs(p1.x - p2.x) < EPSILON and p1.y < p2.y):
            self.p1 = p1
            self.p2 = p2
        else:
            self.p1 = p2
            self.p2 = p1

    def __eq__(self, other):
        return self.p1 == other.p1 and self.p2 == other.p2

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self.p1, self.p2))

    def __str__(self):
        return f"Edge({self.p1}, {self.p2})"

class Triangle:
    """Класс для представления треугольника."""
    def __init__(self, p1: Point, p2: Point, p3: Point):

        self.vertices = tuple(sorted([p1, p2, p3], key=lambda p: (p.x, p.y)))
        self.edges = {
            Edge(self.vertices[0], self.vertices[1]),
            Edge(self.vertices[1], self.vertices[2]),
            Edge(self.vertices[0], self.vertices[2])
        }
        self._circumcenter = None
        self._circumradius_sq = None

    def __eq__(self, other):
        return self.vertices == other.vertices

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.vertices)

    def __str__(self):
        return f"Triangle({self.vertices[0]}, {self.vertices[1]}, {self.vertices[2]})"

    @property
    def circumcenter_radius_sq(self):
        """Вычисляет центр и квадрат радиуса описанной окружности."""
        if self._circumcenter is None:
            p1, p2, p3 = self.vertices
            ax, ay = p1.x, p1.y
            bx, by = p2.x, p2.y
            cx, cy = p3.x, p3.y

            D = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))


            if abs(D) < EPSILON:


                self._circumcenter = Point(float('inf'), float('inf'))
                self._circumradius_sq = float('inf')

                return self._circumcenter, self._circumradius_sq


            ux = ((ax*ax + ay*ay) * (by - cy) + (bx*bx + by*by) * (cy - ay) + (cx*cx + cy*cy) * (ay - by)) / D
            uy = ((ax*ax + ay*ay) * (cx - bx) + (bx*bx + by*by) * (ax - cx) + (cx*cx + cy*cy) * (bx - ax)) / D

            self._circumcenter = Point(ux, uy)

            self._circumradius_sq = self._circumcenter.distance_sq(p1)

        return self._circumcenter, self._circumradius_sq

    def point_in_circumcircle(self, point: Point) -> bool:
        """Проверяет, лежит ли точка внутри описанной окружности."""
        center, radius_sq = self.circumcenter_radius_sq
        if radius_sq == float('inf'):
             return False

        dist_sq = center.distance_sq(point)

        return dist_sq < radius_sq - EPSILON

    def has_vertex(self, point: Point) -> bool:
        """Проверяет, является ли точка вершиной треугольника."""
        return point in self.vertices



def get_super_triangle(points: list[Point], margin_scale=3.0) -> Triangle:
    """Создает супер-треугольник, охватывающий все точки."""
    if not points:

        min_x, max_x = -1000, 1000
        min_y, max_y = -1000, 1000
    else:
        min_x = min(p.x for p in points)
        max_x = max(p.x for p in points)
        min_y = min(p.y for p in points)
        max_y = max(p.y for p in points)

    dx = max_x - min_x
    dy = max_y - min_y
    delta_max = max(dx, dy)
    mid_x = (min_x + max_x) / 2.0
    mid_y = (min_y + max_y) / 2.0


    p1 = Point(mid_x - margin_scale * delta_max, mid_y - margin_scale * delta_max * 0.5)
    p2 = Point(mid_x + margin_scale * delta_max, mid_y - margin_scale * delta_max * 0.5)
    p3 = Point(mid_x, mid_y + margin_scale * delta_max * 1.5)

    return Triangle(p1, p2, p3)

def cross_product(p1: Point, p2: Point, p3: Point) -> float:
    """Векторное произведение векторов (p2-p1) и (p3-p1)."""
    return (p2.x - p1.x) * (p3.y - p1.y) - (p2.y - p1.y) * (p3.x - p1.x)