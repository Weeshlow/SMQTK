#!/usr/bin/env python
import csv
import itertools

from smqtk.representation import (
    get_descriptor_index_impls,
)
from smqtk.utils import (
    bin_utils,
    plugin,
)


def default_config():
    return {
        'plugins': {
            'descriptor_index':
                plugin.make_config(get_descriptor_index_impls()),
        }
    }


def extend_parser(parser):
    g_io = parser.add_argument_group("IO Options")
    g_io.add_argument('-f', metavar='PATH',
                      help='Path to the csv file mapping descriptor UUIDs to '
                           'their class label. String labels are transformed '
                           'into integers for libSVM. Integers start at 1 '
                           'and are applied in the order that labels are '
                           'seen in this input file.')
    g_io.add_argument('-o', metavar='PATH',
                      help='Path to the output file to write libSVM labeled '
                           'descriptors to.')
    return parser


def main():
    description = """
    Utility script to transform a set of descriptors, specified by UUID, with
    matching class labels, to a test file usable by libSVM utilities for
    train/test experiments.

    The input CSV file is assumed to be of the format:

        uuid,label
        ...

    This is the same as the format requested for other scripts like
    ``classifier_model_validation.py``.
    """
    args, config = bin_utils.utility_main_helper(default_config, description,
                                                 extend_parser)

    #: :type: smqtk.representation.DescriptorIndex
    descriptor_index = plugin.from_plugin_config(
        config['plugins']['descriptor_index'],
        get_descriptor_index_impls()
    )

    labels_filepath = args.f
    output_filepath = args.o

    # Run through labeled UUIDs in input file, getting the descriptor from the
    # configured index, applying the appropriate integer label and then writing
    # the formatted line out to the output file.
    input_uuid_labels = csv.reader(open(labels_filepath))

    with open(output_filepath, 'w') as ofile:
        label2int = {}
        next_int = 1
        uuids, labels = zip(*input_uuid_labels)
        for i, (l, d) in enumerate(
                    itertools.izip(labels,
                                   descriptor_index.get_many_descriptors(*uuids))
                ):
            print i, d.uuid()
            if l not in label2int:
                label2int[l] = next_int
                next_int += 1
            ofile.write(
                "%d " % label2int[l] +
                ' '.join(["%d:%.12f" % (j+1, f)
                          for j, f in enumerate(d.vector())
                          if f != 0.0]) +
                '\n'
            )


if __name__ == '__main__':
    main()
