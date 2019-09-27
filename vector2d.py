#!/usr/bin/env python3
from math import sin, cos, atan2, sqrt

class Vector2D:

    def __init__(self, x=None, y=None):
        if y is None:
            if isinstance(x, Polar2D):
                r = x.r
                theta = x.theta
                x = cos(theta) * r
                y = sin(theta) * r
            elif isinstance(x, self.__class__):
                y = x.y
                x = x.x
            elif x is None:
                x = y = 0
            else:
                x, y = x
        self.__dict__['x'] = x
        self.__dict__['y'] = y

    def __repr__(self):
        return f"<{self.__class__.__name__} ({self.x}, {self.y})>"

    def __getitem__(self, index):
        if index == 0:
            return self.x
        if index == 1:
            return self.y
        raise IndexError(f"Index {index} out of range for {self}")

    def __setattr__(self, name, value):
        raise AttributeError(f"{self.__class__.__name__} objects are immutable")

    def __len__(self):
        return 2

    def __iter__(self):
        yield self.x
        yield self.y

    def __add__(self, other):
        if isinstance(other, Polar2D):
            other = self.__class__(other)
            x = other.x
            y = other.y
        elif hasattr(other, '__getitem__'):
            x, y = other
        else:
            x = y = other
        return self.__class__(self.x + x, self.y + y)

    def __radd__(self, other):
        return self.__radd__(other)

    def __sub__(self, other):
        if isinstance(other, Polar2D):
            other = self.__class__(other)
            x = other.x
            y = other.y
        elif hasattr(other, '__getitem__'):
            x, y = other
        else:
            x = y = other
        return self.__class__(self.x - x, self.y - y)

    def dot(self, other):
        if not isinstance(other, Vector2D):
            other = self.__class__(other)
        return sqrt(self.magnitude_squared + other.magnitude_squared) * cos(Polar2D(self).theta - Polar2D(other).theta)

    def __mul__(self, other):
        if not isinstance(other, (int, float)):
            raise ValueError(f"{self.__class__.__name__} can only be multiplied by scalars (int, float)")
        return self.__class__(self.x * other, self.y * other)

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        if not isinstance(other, (int, float)):
            raise ValueError(f"{self.__class__.__name__} can only be divided by scalars (int, float)")
        return self.__class__(self.x / other, self.y / other)

    def __eq__(self, other):
        if isinstance(other, Polar2D):
            other = self.__class__(other)
        return isinstance(other, Vector2D) and (self.x == other.x) and (self.y == other.y)

    def __ne__(self, other):
        return not self.__eq__(other)

    @property
    def magnitude(self):
        magnitude = self.__dict__.get('magnitude')
        if magnitude is None:
            magnitude = sqrt(self.magnitude_squared)
            self.__dict__['magnitude'] = magnitude
        return magnitude

    @property
    def magnitude_squared(self):
        magnitude_squared = self.__dict__.get('magnitude_squared')
        if magnitude_squared is None:
            magnitude_squared = (self.x*self.x) + (self.y*self.y)
            self.__dict__['magnitude_squared'] = magnitude_squared
        return magnitude_squared

    def normalized(self):
        return self / self.magnitude

    def scaled(self, scale):
        return self * (scale / self.magnitude)

    def rotated(self, theta):
        polar = Polar2D(self)
        polar2 = Polar2D(polar.r, polar.theta + theta)
        return self.__class__(polar2)

class Polar2D:
    def __init__(self, r=None, theta=None):
        if theta is None:
            if isinstance(r, Vector2D):
                theta = atan2(r.y, r.x)
                r = r.magnitude
            elif isinstance(x, self.__class__):
                theta = r.theta
                r = r.r
            elif r is None:
                r = theta = 0
            else:
                r, theta = r
        self.__dict__['r'] = r
        self.__dict__['theta'] = theta

    def __repr__(self):
        return f"<{self.__class__.__name__} ({self.r}, {self.theta})>"

    def __getitem__(self, index):
        if index == 0:
            return self.x
        if index == 1:
            return self.y
        raise IndexError(f"Index {index} out of range for {self}")

    def __setattr__(self, name, value):
        raise AttributeError(f"{self.__class__.__name__} objects are immutable")

    def __len__(self):
        return 2

    def __iter__(self):
        yield self.r
        yield self.theta

    def __add__(self, other):
        v2 = Vector2D(self)
        return self.__class__(v2 + other)

    def __sub__(self, other):
        v2 = Vector2D(self)
        return self.__class__(v2 - other)

    def __mul__(self, other):
        if not isinstance(other, (int, float)):
            raise ValueError(f"{self.__class__.__name__} can only be multiplied by scalars (int, float)")
        return self.__class__(Vector2D(self) * other)

    def __eq__(self, other):
        if isinstance(other, Vector2D):
            other = self.__class__(other)
        return isinstance(other, self.__class__) and (self.x == other.x) and (self.y == other.y)

    def __ne__(self, other):
        return not self.__eq__(other)


if __name__ == "__main__":
    v = Vector2D(1, 2)
    w = Vector2D(3, 4)
    print("v", v)
    print("w", w)
    print("v + w", v + w)
    print("v * 3", v * 3)
    print("v - w", v - w)
    x, y = v
    print("x, y", x, y)
    print("v.magnitude", v.magnitude)
    print("w.magnitude", w.magnitude)
    vpolar = Polar2D(v)
    wpolar = Polar2D(w)
    sumpolar = vpolar + wpolar
    print("v polar", vpolar)
    print("w polar", wpolar)
    print("sum polar", sumpolar)
    vprime = Vector2D(vpolar)
    wprime = Vector2D(wpolar)
    sumprime = Vector2D(sumpolar)
    print("vprime", vprime)
    print("wprime", wprime)
    print("sum prime", sumprime)
    another_v = Vector2D([1, 2])
    assert v == another_v
    assert v != w


