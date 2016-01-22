import abc
import os

from smqtk.representation import SmqtkRepresentation
from smqtk.utils import plugin

from ._exceptions import *


__author__ = "paul.tunison@kitware.com"


class ClassificationElement(SmqtkRepresentation, plugin.Pluggable):
    """
    Classification result encapsulation.

    Contains a mapping of arbitrary (but hashable) label values to confidence
    values (floating point in ``[0,1]`` range). If a classifier does no produce
    continuous confidence values, it may instead assign a value of ``1.0`` to a
    single label, and ``0.0`` to the rest.

    UUIDs must maintain unique-ness when transformed into a string.

    The sum of all values should be ``1.0``.

    """

    def __init__(self, type_name, uuid):
        """
        Initialize a new classification element.

        :param type_name: Name of the type of classifier this classification was
            generated by.
        :type type_name: str

        :param uuid: Unique ID reference of the classification
        :type uuid: collections.Hashable

        """
        super(ClassificationElement, self).__init__()
        self.type_name = type_name
        self.uuid = uuid

    def __hash__(self):
        return hash((self.type_name, self.uuid))

    def __eq__(self, other):
        if isinstance(other, ClassificationElement):
            try:
                a = self.get_classification()
            except NoClassificationError:
                a = None
            try:
                b = other.get_classification()
            except NoClassificationError:
                b = None
            return a == b
        return False

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        return "%s{type_name: %s, uuid: %s}" \
            % (self.__class__.__name__, self.type_name, self.uuid)

    def __getitem__(self, label):
        """
        Get the confidence value for a specific label

        :param label: Classification label to get the confidence value for.
        :type label: collections.Hashable

        :raises KeyError: The given label is not present in this classification.
        :raises NoClassificationError: No classification labels/confidences yet
            set.

        :return: Confidence value for the given label.
        :rtype: float

        """
        return self.get_classification()[label]

    @classmethod
    def get_default_config(cls):
        """
        Generate and return a default configuration dictionary for this class.
        This will be primarily used for generating what the configuration
        dictionary would look like for this class without instantiating it.

        By default, we observe what this class's constructor takes as arguments,
        turning those argument names into configuration dictionary keys. If any
        of those arguments have defaults, we will add those values into the
        configuration dictionary appropriately. The dictionary returned should
        only contain JSON compliant value types.

        It is not be guaranteed that the configuration dictionary returned
        from this method is valid for construction of an instance of this class.

        :return: Default configuration dictionary for the class.
        :rtype: dict

        """
        # similar to parent impl, except we remove the ``type_str`` and ``uuid``
        # configuration parameters as they are to be specified at runtime.
        dc = super(ClassificationElement, cls).get_default_config()
        # These parameters must be specified at construction time.
        del dc['type_name'], dc['uuid']
        return dc

    # noinspection PyMethodOverriding
    @classmethod
    def from_config(cls, config_dict, type_name, uuid):
        """
        Instantiate a new instance of this class given the configuration
        JSON-compliant dictionary encapsulating initialization arguments.

        This method should not be called via super unless and instance of the
        class is desired.

        :param config_dict: JSON compliant dictionary encapsulating
            a configuration.
        :type config_dict: dict

        :param type_name: Name of the type of classifier this classification was
            generated by.
        :type type_name: str

        :param uuid: Unique ID reference of the classification
        :type uuid: collections.Hashable

        :return: Constructed instance from the provided config.
        :rtype: ClassificationElement

        """
        c = {}
        c.update(config_dict)
        c['type_name'] = type_name
        c['uuid'] = uuid
        return super(ClassificationElement, cls).from_config(c)

    def max_label(self):
        """
        Get the label with the highest confidence.

        :raises NoClassificationError: No classification set.

        :return: The label with the highest confidence.
        :rtype: collections.Hashable

        """
        m = (None, 0.)
        for i in self.get_classification().iteritems():
            if i[1] > m[1]:
                m = i
        return m[0]

    #
    # Abstract methods
    #

    @abc.abstractmethod
    def has_classifications(self):
        """
        :return: If this element has classification information set.
        :rtype: bool
        """

    @abc.abstractmethod
    def get_classification(self):
        """
        Get classification result map, returning a label-to-confidence dict.

        We do no place any guarantees on label value types as they may be
        represented in various forms (integers, strings, etc.).

        Confidence values are in the [0,1] range.

        :raises NoClassificationError: No classification labels/confidences yet
            set.

        :return: Label-to-confidence dictionary.
        :rtype: dict[collections.Hashable, float]

        """

    @abc.abstractmethod
    def set_classification(self, m=None, **kwds):
        """
        Set the whole classification map for this element. This will strictly
        overwrite the entire label-confidence mapping (vs. updating it)

        Label/confidence values may either be provided via keyword arguments or
        by providing a dictionary mapping labels to confidence values.

        The sum of all confidence values, must be ``1.0`` (e.g. input cannot be
        empty). Due to possible floating point error, we round to the 9-th
        decimal digit.

        NOTE TO IMPLEMENTORS: This abstract method will aggregate, and error
        check, input into a single dictionary and return it. Thus, a ``super``
        call should be made, which will return a dictionary.

        :param m: New labels-to-confidence mapping to set.
        :type m: dict[collections.Hashable, float]

        :raises ValueError: The given label-confidence map was empty or values
            did no sum to ``1.0``.

        """
        ROUND = 9
        m = m or {}
        m.update(kwds)
        s = sum(m.values())
        if round(s, ROUND) != 1.0:
            raise ValueError("Classification map values do not sum "
                             "sufficiently close to 1.0 (actual = %f)"
                             % s)
        return m


def get_classification_element_impls(reload_modules=False):
    """
    Discover and return discovered ``ClassificationElement`` classes. Keys in
    the returned map are the names of the discovered classes, and the paired
    values are the actual class type objects.

    We search for implementation classes in:
        - modules next to this file this function is defined in (ones that begin
          with an alphanumeric character),
        - python modules listed in the environment variable
          ``CLASSIFICATION_ELEMENT_PATH``
            - This variable should contain a sequence of python module
              specifications, separated by the platform specific PATH separator
              character (``;`` for Windows, ``:`` for unix)

    Within a module we first look for a helper variable by the name
    ``CLASSIFICATION_ELEMENT_CLASS``, which can either be a single class object
    or an iterable of class objects, to be specifically exported. If the
    variable is set to None, we skip that module and do not import anything. If
    the variable is not present, we look at attributes defined in that module
    for classes that descend from the given base class type. If none of the
    above are found, or if an exception occurs, the module is skipped.

    :param reload_modules: Explicitly reload discovered modules from source.
    :type reload_modules: bool

    :return: Map of discovered class object of type ``Classifier``
        whose keys are the string names of the classes.
    :rtype: dict[str, type]

    """
    this_dir = os.path.abspath(os.path.dirname(__file__))
    env_var = "CLASSIFICATION_ELEMENT_PATH"
    helper_var = "CLASSIFICATION_ELEMENT_CLASS"
    return plugin.get_plugins(__name__, this_dir, env_var, helper_var,
                              ClassificationElement,
                              reload_modules=reload_modules)
