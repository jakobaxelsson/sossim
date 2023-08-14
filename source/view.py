"""
Module containing functionality for attaching views to model classes.    
"""
from typing import Any, Protocol

class View(Protocol):
    """
    Interface class for views.
    """
    def update(self, viewable: Any):
        """
        Updates the view. This is an abstract function that is redefined in subclasses.

        Args:
            viewable (Any): the viewable on which the update should be based.
        """

def viewable(cls):
    """
    A mixin decorator for objects to which a view can be attached. 
    It adds the methods for handling views attached to the viewable, unless such a method already exists.
    """
    def add_view(self, view: View):
        """
        Adds a view to the viewable object.

        Args:
            view (Any): the view.
        """
        if not hasattr(self, "_views"):
            self._views = []
        self._views += [view]
        self.update_views()

    def get_views(self) -> list[View]:
        """
        Returns the list of views attached to the viewable object.

        Returns:
            list[View]: the views.
        """
        if not hasattr(self, "_views"):
            self._views = []
        return self._views

    def update_views(self):
        """
        Updates the views.
        """
        if not hasattr(self, "_views"):
            self._views = []
        for view in self._views:
            view.update(self)

    def clear_views(self):
        """
        Removes all views.
        """
        self._views = []

    setattr(cls, "add_view", add_view)
    setattr(cls, "get_views", get_views)
    setattr(cls, "update_views", update_views)
    setattr(cls, "clear_views", clear_views)
    return cls