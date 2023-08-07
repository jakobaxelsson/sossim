"""
Module containing functionality for attaching views to model classes.    
"""
from typing import List

class View:
    """
    Base class for views.
    """
    def update(self, viewable: "Viewable"):
        """
        Updates the view. This is an abstract function that is redefined in subclasses.

        Args:
            viewable (Viewable): the viewable on which the update should be based.
        """
        pass

class Viewable:
    """
    A mixin for objects to which a view can be attached. It adds the methods add_view and update_views.
    """
    def add_view(self, view: View):
        """
        Adds a view to the viewable element.

        Args:
            view (Any): the view.
        """
        if not hasattr(self, "_views"):
            self._views = []
        self._views += [view]
        self.update_views()

    def get_views(self) -> List[View]:
        """
        Returns the list of views attached to the viewable object.

        Returns:
            List[View]: the views.
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