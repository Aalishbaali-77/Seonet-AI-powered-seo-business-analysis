from rest_framework.throttling import AnonRateThrottle


class AuthBurstThrottle(AnonRateThrottle):
    scope = "auth"
