from .bilibili import BilibiliSource
from .xhs import XhsSource

REGISTRY = {"bilibili": BilibiliSource, "xhs": XhsSource}
