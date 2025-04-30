from geometry import Point, Triangle, Edge, get_super_triangle
import time

class DelaunayTriangulation:
    """Класс для вычисления триангуляции Делоне."""

    def __init__(self, points: list[Point]):
        self.points = list(set(points))
        self.triangles: set[Triangle] = set()
        self._super_triangle: Triangle | None = None
        self._super_vertices: tuple[Point, Point, Point] | None = None

    def triangulate(self, step_callback=None, delay=0.1):
        """Выполняет триангуляцию."""
        self.triangles.clear()
        if len(self.points) < 3:

            if len(self.points) == 2:

                 pass
            if step_callback: step_callback({'final': self.triangles.copy()})
            return list(self.triangles)


        self._super_triangle = get_super_triangle(self.points)
        self._super_vertices = self._super_triangle.vertices
        self.triangles.add(self._super_triangle)
        if step_callback:
            step_callback({'init': True, 'super_triangle': self._super_triangle, 'triangles': self.triangles.copy()})
            time.sleep(delay)


        for i, point in enumerate(self.points):
            bad_triangles: set[Triangle] = set()
            polygon_edges: list[Edge] = []


            for triangle in self.triangles:
                if triangle.point_in_circumcircle(point):
                    bad_triangles.add(triangle)

            if step_callback:
                 step_callback({'point': point, 'bad_triangles': bad_triangles.copy(), 'triangles': self.triangles.copy()})
                 time.sleep(delay*1.5)



            edge_counts = {}
            for triangle in bad_triangles:
                for edge in triangle.edges:
                    edge_counts[edge] = edge_counts.get(edge, 0) + 1

            for edge, count in edge_counts.items():
                if count == 1:
                    polygon_edges.append(edge)


            self.triangles -= bad_triangles

            if step_callback:
                step_callback({
                    'hole_edges': polygon_edges.copy(),
                    'triangles': self.triangles.copy()
                })
                time.sleep(delay*1.5)


            new_triangles: set[Triangle] = set()
            for edge in polygon_edges:
                new_triangle = Triangle(edge.p1, edge.p2, point)
                new_triangles.add(new_triangle)
                self.triangles.add(new_triangle)

            if step_callback:
                 step_callback({'new_triangles': new_triangles, 'triangles': self.triangles.copy()})
                 time.sleep(delay)


        final_triangles: set[Triangle] = set()
        for triangle in self.triangles:
            is_connected_to_super = False
            for vertex in triangle.vertices:
                if vertex in self._super_vertices:
                    is_connected_to_super = True
                    break
            if not is_connected_to_super:
                final_triangles.add(triangle)

        self.triangles = final_triangles

        if step_callback:
            step_callback({'final': self.triangles.copy()})

        return list(self.triangles)


    def triangulate_stepwise(self):
        """Генератор для пошаговой триангуляции."""
        self.triangles.clear()
        state = {}
        if len(self.points) < 3:
            state = {'status': 'done', 'final': set()}
            yield state
            return


        self._super_triangle = get_super_triangle(self.points)
        self._super_vertices = self._super_triangle.vertices
        self.triangles.add(self._super_triangle)
        state = {
            'status': 'init',
            'super_triangle': self._super_triangle,
            'triangles': self.triangles.copy(),
            'message': 'Инициализация: Супер-треугольник добавлен.'
        }
        yield state


        for i, point in enumerate(self.points):
            bad_triangles: set[Triangle] = set()
            polygon_edges: list[Edge] = []


            state = {
                'status': 'point_select',
                'point': point,
                'triangles': self.triangles.copy(),
                'message': f'Шаг {i+1}.1: Добавляем точку {point}.'
            }
            yield state


            for triangle in self.triangles:
                if triangle.point_in_circumcircle(point):
                    bad_triangles.add(triangle)

            state = {
                'status': 'find_bad',
                 'point': point,
                'bad_triangles': bad_triangles.copy(),
                'triangles': self.triangles.copy(),
                'message': f'Шаг {i+1}.2: Найдены "плохие" треугольники (точка внутри их описанной окружности).'
            }
            yield state


            edge_counts = {}
            for triangle in bad_triangles:
                for edge in triangle.edges:
                    edge_counts[edge] = edge_counts.get(edge, 0) + 1
            for edge, count in edge_counts.items():
                if count == 1:
                    polygon_edges.append(edge)

            self.triangles -= bad_triangles
            state = {
                'status': 'make_hole',
                 'point': point,
                'bad_triangles': bad_triangles.copy(),
                'hole_edges': polygon_edges.copy(),
                'triangles': self.triangles.copy(),
                 'message': f'Шаг {i+1}.3: Удалены плохие треугольники, сформирована "дыра".'
            }
            yield state


            new_triangles: set[Triangle] = set()
            for edge in polygon_edges:
                try:

                    if abs(cross_product(edge.p1, edge.p2, point)) > EPSILON:
                         new_triangle = Triangle(edge.p1, edge.p2, point)
                         new_triangles.add(new_triangle)
                         self.triangles.add(new_triangle)

                        # print(f"Предупреждение: Пропуск создания вырожденного треугольника с точкой {point} и ребром {edge}")
                except Exception as e:
                    print(f"Ошибка при создании треугольника: {e} с точкой {point} и ребром {edge}")


            state = {
                'status': 'fill_hole',
                 'point': point,
                 'hole_edges': polygon_edges.copy(),
                'new_triangles': new_triangles.copy(),
                'triangles': self.triangles.copy(),
                 'message': f'Шаг {i+1}.4: Дыра заполнена новыми треугольниками.'
            }
            yield state


        final_triangles: set[Triangle] = set()
        removed_super_triangles: set[Triangle] = set()
        for triangle in self.triangles:
            is_connected_to_super = False
            for vertex in triangle.vertices:
                if vertex in self._super_vertices:
                    is_connected_to_super = True
                    break
            if not is_connected_to_super:
                final_triangles.add(triangle)
            else:
                removed_super_triangles.add(triangle)

        self.triangles = final_triangles
        state = {
            'status': 'finalize',
            'removed_super': removed_super_triangles,
            'final': self.triangles.copy(),
            'message': 'Финализация: Удалены треугольники, связанные с супер-треугольником.'
        }
        yield state

        state = {'status': 'done', 'final': self.triangles.copy(), 'message': 'Триангуляция Делоне завершена.'}
        yield state