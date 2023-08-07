"""
Module containing functionality for attaching views to model classes.    
"""
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
    A mixin for objects to which a view can be attached. It adds the methods add_view and update_view.
    """
    def add_view(self, view: View):
        """
        Adds a view to the viewable element.

        Args:
            view (Any): the view.
        """
        self._view = view
        self.update_view()

    def get_view(self) -> View:
        """
        Returns the view attached to the viewable object, if any.

        Returns:
            Any: the view (or None).
        """
        return self._view

    def update_view(self):
        """
        Updates the view, if one exists.
        """
        if hasattr(self, "_view") and self._view:
            self._view.update(self)