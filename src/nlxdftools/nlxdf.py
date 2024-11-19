"""Class for working with Neurolive/AntNeuro XDF data files."""

from collections import Counter

import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd
from pyxdftools import Xdf, XdfDecorators
from pyxdftools.errors import NoLoadableStreamsError, XdfAlreadyLoadedError

from nlxdftools.plotting import format_load_params, format_title


class NlXdf(Xdf):
    """Class for working with individual Neurolive/AntNeuro XDF data files.

    Provides a pandas-based layer of abstraction over raw XDF data to
    simplify data processing.
    """

    hostname_device_mapper = {
        'DESKTOP-3R7C1PH': 'eeg-a',
        'DESKTOP-2TI6RBU': 'eeg-b',
        'DESKTOP-MN7K6RM': 'eeg-c',
        'DESKTOP-URRV98M': 'eeg-d',
        'DESKTOP-DATOEVU': 'eeg-e',
        'TABLET-9I44R1AR': 'eeg-f',
        'DESKTOP-SLAKFQE': 'eeg-g',
        'DESKTOP-6FJTJJN': 'eeg-h',
        'DESKTOP-HDOESKS': 'eeg-i',
        'DESKTOP-LIA3G09': 'eeg-j',
        'DESKTOP-V6779I4': 'eeg-k',
        'DESKTOP-PLV2A7L': 'eeg-l',
        'DESKTOP-SSSOE1L': 'eeg-m',
        'DESKTOP-RM16J67': 'eeg-n',
        'DESKTOP-N2RA68S': 'eeg-o',
        'DESKTOP-S597Q21': 'eeg-p',
        'TABLET-06K1PLD4': 'eeg-q',
        'DESKTOP-MK0GQFM': 'eeg-r',
        'DESKTOP-7GV3RJU': 'eeg-s',
        'DESKTOP-S5A1PPK': 'eeg-t',
        'TABLET-3BS4NTP2': 'eeg-u',
        'DESKTOP-QG4CNEV': 'eeg-v',
        'DESKTOP-OAF4OCM': 'eeg-w',
        'TABLET-47TCFCEB': 'eeg-cs-v', # DESKTOP-T3RKRMH?
        'CGS-PCD-26098': 'tabarnak',
        'CGS-PCL-38928': 'laura',
        'cgs-macl-39034.campus.goldsmiths.ac.uk': 'mirko',
        'kassia': 'jamief',
    }

    metadata_mapper = {
        'type': {
            'EEG': 'eeg',
            #'marker': 'Timestamp',
        },
    }

    channel_metadata_mapper = {
        'label': {
            '0': 'Fp1',
            '1': 'Fpz',
            '2': 'Fp2',
            '3': 'F7',
            '4': 'F3',
            '5': 'Fz',
            '6': 'F4',
            '7': 'F8',
            '8': 'FC5',
            '9': 'FC1',
            '10': 'FC2',
            '11': 'FC6',
            '12': 'M1',
            '13': 'T7',
            '14': 'C3',
            '15': 'Cz',
            '16': 'C4',
            '17': 'T8',
            '18': 'M2',
            '19': 'CP5',
            '20': 'CP1',
            '21': 'CP2',
            '22': 'CP6',
            '23': 'P7',
            '24': 'P3',
            '25': 'Pz',
            '26': 'P4',
            '27': 'P8',
            '28': 'POz',
            '29': 'O1',
            '30': 'Oz',
            '31': 'O2',
            '32': 'Resp',  # EEG 101 with 34 channels?
            '67': 'CPz',
            '33': 'trigger',
            '34': 'counter',
        },
        'type': {
            'ref': 'eeg',
            'aux': 'misc',
            'bip': 'misc',
            'trigger': 'misc',
            'counter': 'misc',
            'trg': 'stim'
        },
    }

    def resolve_streams(self, nl_id_as_index=True):
        """Resolve XDF streams from file using pyxdf.resolve_stream().

        Apply custom device name mapping for Neurolive analysis.
        """
        df = super().resolve_streams()
        nl_ids = self._create_nl_ids(df)
        df['nl_id'] = nl_ids
        if nl_id_as_index:
            # Set nl_id as the index.
            df.reset_index(inplace=True)
            df.set_index('nl_id', inplace=True, verify_integrity=True)
            df.sort_index(inplace=True)
        else:
            # Append nl_id as a new column.
            cols = df.columns.tolist()
            # Move nl_id to first column.
            cols = cols[-1:] + cols[0:-1]
            df = df[cols]
        return df

    def load(
            self,
            *select_streams,
            channel_scale_field='unit',
            channel_name_field='label',
            synchronize_clocks=True,
            dejitter_timestamps=True,
            handle_clock_resets=True,
            **kwargs):
        """Load XDF data from file using pyxdf.load_xdf().

        Apply custom defaults for Neurolive analysis.
        """
        try:
            self._load(*select_streams,
                       channel_scale_field=channel_scale_field,
                       channel_name_field=channel_name_field,
                       synchronize_clocks=synchronize_clocks,
                       dejitter_timestamps=dejitter_timestamps,
                       handle_clock_resets=handle_clock_resets,
                       **kwargs)
        except (NoLoadableStreamsError, XdfAlreadyLoadedError) as exc:
            print(exc)
            return self

        # Map stream-IDs to neurolive IDs.
        self._loaded_stream_ids = self._map_stream_ids(self.loaded_stream_ids)
        self._channel_metadata = self._map_stream_ids(self._channel_metadata)
        self._footer = self._map_stream_ids(self._footer)
        self._clock_offsets = self._map_stream_ids(self._clock_offsets)
        self._time_series = self._map_stream_ids(self._time_series)
        self._time_stamps = self._map_stream_ids(self._time_stamps)
        return self

    def _parse_metadata(self, data, nl_id_as_index=True, **kwargs):
        """Map neurolive stream ids and types."""
        df = super()._parse_metadata(data, **kwargs)
        # Lowercase types following MNE convention.
        df['type'] = df['type'].str.lower()
        # Fix-up metadata types.
        df.replace(self.metadata_mapper, inplace=True)
        nl_ids = self._create_nl_ids(df)
        df['nl_id'] = nl_ids
        if nl_id_as_index:
            # Set nl_id as the index.
            df.reset_index(inplace=True)
            df.set_index('nl_id', inplace=True, verify_integrity=True)
            df.sort_index(inplace=True)
        else:
            # Append nl_id as a new column.
            cols = df.columns.tolist()
            # Move nl_id to first column.
            cols = cols[-1:] + cols[0:-1]
            df = df[cols]
        return df

    def _parse_channel_metadata(self, data, **kwargs):
        """Map AntNeuro stream ids and channel names."""
        data = super()._parse_channel_metadata(data, **kwargs)
        if data is not None:
            for df in data.values():
                # For AntNeuro App which doesn't include channel labels.
                if 'index' in df and 'label' not in df:
                    df['label'] = df['index']
                df.replace(self.channel_metadata_mapper,
                           inplace=True)
        return data

    def _create_nl_ids(self, df):

        unique_id_counter = Counter()

        def make_nl_id(row, unique_id_counter, hostname_map):
            # Fallback to stream_id as string.
            nl_id = str(row.name)
            if row['type'].lower() == 'eeg':
                # Map EEG devices.
                nl_id = hostname_map[row['hostname']]
            elif row['name'] == 'TimestampStream':
                nl_id = 'ts-marker'
            elif row['name'] == 'CameraRecordingTime':
                nl_id = 'ts-video'
            elif row['type'] == 'marker' and row['name'] == 'audio':
                # Map audio device.
                nl_id = 'ts-audio'
            elif row['name'].lower().startswith('pupil'):
                if row['type'].lower() == 'event':
                    nl_id = f'pl-{row["source_id"]}-event'
                elif row['type'].lower() == 'gaze':
                    nl_id = f'pl-{row["source_id"]}-gaze'
            elif row['type'] == 'data' and row['name'].startswith('Test'):
                if row['hostname'] in ['neurolive', 'bobby']:
                    # Sync test running on the LabRecorder host -- the
                    # closest thing we have to a ground truth.
                    nl_id = 'test-ref'
                elif row['hostname'] in hostname_map:
                    # Sync test running on an EEG tablet.
                    nl_id = f'test-{hostname_map[row["hostname"]]}'
                else:
                    # Sync test running on another device.
                    nl_id = 'test'
            elif row['type'] == 'control':
                # Sync test control stream.
                nl_id = 'test-ctrl'
            elif row['type'].lower() == 'markers':
                nl_id = nl_id + '-markers'
            elif row['name'].startswith('_relay_'):
                nl_id = nl_id + '-relay'
            unique_id_counter.update([nl_id])
            if unique_id_counter[nl_id] > 1:
                nl_id = f'{nl_id}-{unique_id_counter[nl_id]}'
            return nl_id

        nl_ids = df.apply(
            make_nl_id,
            axis='columns',
            unique_id_counter=unique_id_counter,
            hostname_map=self.hostname_device_mapper,
        )
        return nl_ids

    def _map_stream_ids(self, data):
        if data is None:
            return data
        if isinstance(data, list):
            data = [self._stream_id_to_nl_id(stream_id)
                    for stream_id in data]
            data.sort()
        elif isinstance(data, dict):
            data = {self._stream_id_to_nl_id(stream_id): df
                    for stream_id, df in data.items()}
            data = dict(sorted(data.items()))
        elif isinstance(data, pd.DataFrame):
            data.rename(index=self._stream_id_to_nl_id, inplace=True)
            data.sort_index(inplace=True)
        return data

    def _stream_id_to_nl_id(self, stream_id):
        nl_id = self._metadata.index[
            self._metadata['stream_id'] == stream_id
        ][0]
        return nl_id

    @XdfDecorators.loaded
    def plot_data(self, *stream_ids, exclude=[], cols=None):
        data = self.data(*stream_ids,
                         exclude=exclude,
                         cols=cols,
                         with_stream_id=True)
        with mpl.rc_context({'axes.prop_cycle':
                             plt.cycler('color', plt.cm.tab20.colors)}):
            fig, ax = plt.subplots(1)
            for stream_id, df in data.items():
                df = pd.concat({stream_id: df}, axis=1)
                df.plot(ax=ax)
            title = 'XDF data'
            title = format_title(title, df)
            ax.set_title(title)
            ax.text(x=1.0, y=1.0, s=format_load_params(df), fontsize=7,
                    transform=ax.transAxes,
                    horizontalalignment='left',
                    verticalalignment='bottom')
            ax.legend(bbox_to_anchor=(1, 1), loc=2)
            ax.set_xlabel('time')
            ax.set_ylabel('value')
        return ax

    @XdfDecorators.loaded
    def plot_data_box(self, *stream_ids, exclude=[], cols=None):
        if cols is not None and not isinstance(cols, list):
            cols = [cols]
        df = self.data(*stream_ids,
                       exclude=exclude,
                       cols=cols,
                       with_stream_id=True,
                       as_single_df=True)
        with mpl.rc_context({'axes.prop_cycle':
                             plt.cycler('color', plt.cm.tab20.colors)}):
            ax = df.plot.box(vert=False)
            ax.invert_yaxis()
            title = 'XDF data'
            title = format_title(title, df)
            ax.set_title(title)
            ax.text(x=1.0, y=1.0, s=format_load_params(df), fontsize=7,
                    transform=ax.transAxes,
                    horizontalalignment='left',
                    verticalalignment='bottom')
            ax.set_xlabel('value')
        return ax
