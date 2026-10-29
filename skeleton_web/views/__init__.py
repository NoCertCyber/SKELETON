"""The Flask blueprints, one module per group of routes.

Each exposes `blueprint(svc)`, which closes over the Services bundle and hands
back a Blueprint.  Views reach into the services; nothing in the services
reaches back, so there is one import direction and no cycles.
"""
from . import engagement, launcher, modules, notes, system, terminal

ALL = (launcher, notes, engagement, terminal, modules, system)
