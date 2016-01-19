class PageStats:
    """
    Represents a revision's metadata.
    """
    __slots__ = ('view', 'alter_views', 'inlinks', 'alter_inlinks',
                 'inlinks_from_related')

    def __init__(self, views, alter_views, inlinks, alter_inlinks,
                 inlinks_from_related):
        self.views = int(views)
        self.alter_views = int(views)
        self.inlinks = int(inlinks)
        self.alter_inlinks = int(alter_inlinks)
        self.inlinks_from_related = int(inlinks_from_related) \
                                    if inlinks_from_related else None
