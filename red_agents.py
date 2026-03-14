import math


class RedAgent:
    def __init__(self, name, lat, lon, behavior="patrol"):
        self.name = name
        self.lat = lat
        self.lon = lon
        self.behavior = behavior
        self.waypoints = []
        self.current_wp = 0
        self.state = "PATROL"

    def distance(self, lat, lon):
        return math.sqrt((self.lat - lat) ** 2 + (self.lon - lon) ** 2)

    def patrol(self):
        if not self.waypoints:
            return

        target = self.waypoints[self.current_wp]

        # move slightly toward waypoint
        self.lat += (target[0] - self.lat) * 0.02
        self.lon += (target[1] - self.lon) * 0.02

        if self.distance(target[0], target[1]) < 0.05:
            self.current_wp = (self.current_wp + 1) % len(self.waypoints)

    def evade(self, uavs):
        closest = None
        closest_dist = 999.0

        for uav in uavs:
            distance = self.distance(uav["lat"], uav["lon"])
            if distance < closest_dist:
                closest = uav
                closest_dist = distance

        if closest is None:
            return

        # Move away from the nearest UAV.
        self.lat += (self.lat - closest["lat"]) * 0.05
        self.lon += (self.lon - closest["lon"]) * 0.05

    def decide(self, uavs):
        self.state = "PATROL"

        for uav in uavs:
            if self.distance(uav["lat"], uav["lon"]) < 1.0:
                self.state = "EVADE"
                return self.state

        return self.state

    def update(self, uavs):
        self.decide(uavs)

        if self.state == "PATROL":
            self.patrol()
        elif self.state == "EVADE":
            self.evade(uavs)
