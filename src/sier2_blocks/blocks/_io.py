#

# Various I/O blocks.
#

import os
import param

import pandas as pd
import panel as pn

from sier2 import Block
from pathlib import Path
from io import StringIO, BytesIO

class LoadDataFrame(Block):
    """ GUI import from csv/excel file.

    """

    # Unfortunately, file selection in Panel is dodgy.
    # We need to use a FileInput widget, which uploads the file as a bytes object.
    #
    in_file = param.Bytes(label='Input File', doc='Bytes object of the input file.')
    in_header_row = param.Integer(label='Header row', default=0)
    out_df = param.DataFrame()

    def __init__(self, *args, block_pause_execution=True, **kwargs):
        super().__init__(*args, block_pause_execution=block_pause_execution, **kwargs)

        self.i_if = pn.widgets.FileInput.from_param(
            self.param.in_file,
            accept='.csv,.xlsx,.xls',
            multiple=False
        )

    def execute(self):
        pn.state.notifications.info('Reading file', duration=5_000)

        try:
            if self.i_if.filename.endswith('.csv'):
                self.out_df = pd.read_csv(StringIO(self.in_file.decode('utf-8')), header=self.in_header_row)
            elif self.i_if.filename.endswith('.xlsx') or self.i_if.filename.endswith('.xls'):
                self.out_df = pd.read_excel(BytesIO(self.in_file), header=self.in_header_row)

        except Exception as e:
            pn.state.notifications.error(f'Error reading {self.i_if.filename}. Check sidebar logs for more information.', duration=10_000)
            self.logger.error(str(e))
            #TODO: add feature to logger to send logs to Dag developer

    def __panel__(self):
        i_hr = pn.Param(
            self,
            parameters=['in_header_row'],
            widgets={
                'in_header_row': pn.widgets.IntInput
            }
        )
        return pn.Column(self.i_if, i_hr)

class SaveDataFrame(Block):
    """ Save a dataframe to a csv or xlsx.   
    """

    in_df = param.DataFrame()
    in_file_name = param.String()
    in_subset_len = param.Integer(label='Records to save', default=None)
    in_subset_type = param.String(label='Subset type', default='All')
    
    # Preferred to use default_filename=None and then set a default value like default_filename = '' if not default_filename else default_filename
    def __init__(self, *args, default_filename=None, **kwargs):
        super().__init__(*args, **kwargs)

        # We want to dynamically enable/disable buttons as the user sets the filename and subset info, 
        # so we declare widgets explicitly.

        # We should tell the user how big the file is going to be, just in case.
        #
        self.size_msg = pn.widgets.StaticText(
            value=''
        )

        self.i_fn = pn.widgets.TextInput.from_param(
            self.param.in_file_name,
            placeholder='Output file name',
            value='' if not default_filename else default_filename,
            name='Output file name (without extension)'
        )

        self.i_sub_l = pn.widgets.IntInput.from_param(
            self.param.in_subset_len, 
            value=100, 
            step=10, 
            start=0,
            disabled=True,
        )

        self.i_sub_t = pn.widgets.ToggleGroup.from_param(
            self.param.in_subset_type,
            options=['All', 'Head', 'Tail', 'Random sample'], 
            behavior="radio",
        )
        
        self.csvdl = pn.widgets.FileDownload(
            callback=self.download_csv,
            button_type='success',
            filename='',
            label='Download .csv'
        )

        self.xlsxdl = pn.widgets.FileDownload(
            callback=self.download_xlsx,
            button_type='success',
            filename='',
            label='Download .xlsx'
        )

        self.csvdl.disabled = True
        self.xlsxdl.disabled = True

        # Hook up the filename widget to the download widget.
        # Make sure to watch value_input, which is updated live as the user edits the TextInput.
        # 'value' is only updated if the user hits enter.
        #
        def update_name(event):
            if self.i_fn.value_input:
                self.xlsxdl.disabled = False
                self.xlsxdl.filename = f'{self.i_fn.value_input}.xlsx'
                self.csvdl.disabled = False
                self.csvdl.filename = f'{self.i_fn.value_input}.csv'
            else:
                self.xlsxdl.disabled = True
                self.csvdl.disabled = True

        self.i_fn.param.watch(update_name, 'value_input')

        # Make sure we disable the subset length selection if we're saving everything.
        def update_subset(event):
            if self.i_sub_t.value == 'All':
                self.i_sub_l.value = self.in_df.shape[0]
                self.i_sub_l.disabled = True
            else:
                self.i_sub_l.value = 100
                self.i_sub_l.disabled = False

        self.i_sub_t.param.watch(update_subset, 'value')

    def download_csv(self):
        buf = StringIO()
        if self.in_df is not None:
            if self.in_subset_type == 'All':
                self.in_df.to_csv(buf)
            elif self.in_subset_type == 'Head':
                self.in_df.head(self.in_subset_len).to_csv(buf)
            elif self.in_subset_type == 'Tail':
                self.in_df.tail(self.in_subset_len).to_csv(buf)
            elif self.in_subset_type == 'Random sample':
                self.in_df.sample(self.in_subset_len).to_csv(buf)
            else:
                # We shouldn't ever end up here.
                raise NotImplementedError
            
            buf.seek(0)
            return buf
        else:
            pn.state.notifications.error(f"Error: The Dataframe is empty", duration=10_000)
            
    def download_xlsx(self):
        buf = BytesIO()
        writer = pd.ExcelWriter(buf, engine='xlsxwriter')
        if self.in_df is not None:
            if self.in_subset_type == 'All':
                self.in_df.to_excel(writer)
            elif self.in_subset_type == 'Head':
                self.in_df.head(self.in_subset_len).to_excel(writer)
            elif self.in_subset_type == 'Tail':
                self.in_df.tail(self.in_subset_len).to_excel(writer)
            elif self.in_subset_type == 'Random sample':
                self.in_df.sample(self.in_subset_len).to_excel(writer)
            else:
                # We shouldn't ever end up here.
                raise NotImplementedError
                
            writer.close()
            buf.seek(0)
            return buf
        else:
            pn.state.notifications.error(f"Error: The Dataframe is empty", duration=10_000)

    def execute(self):
        if self.in_df is not None:
            self.size_msg.value = f'Saving data frame of size {self.in_df.shape}.'

            # Only allow file download if we've set an input.
            #
            if self.i_fn.value_input:
                self.csvdl.disabled = False
                self.xlsxdl.disabled = False

            self.i_sub_l.value = self.in_df.shape[0]
        
    def __panel__(self):
        return pn.Column(
            self.size_msg,
            self.i_fn,
            self.i_sub_t,
            self.i_sub_l,
            pn.Row(self.csvdl, self.xlsxdl),
        )

