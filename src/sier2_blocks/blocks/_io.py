#

# Various I/O blocks.
#

import os
import param

import pandas as pd
import panel as pn

from sier2 import InputBlock, Block
from pathlib import Path
from io import StringIO, BytesIO

class LoadDataFrame(InputBlock):
    """ GUI import from csv/excel file.
    
    """

    # Unfortunately, file selection in Panel is dodgy.
    # We need to use a FileInput widget, which uploads the file as a bytes object.
    #
    in_file = param.Bytes(label='Input File', doc='Bytes object of the input file.')
    in_header_row = param.Integer(label='Header row', default=0)
    out_df = param.DataFrame()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
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
            pn.state.notifications.error('Error reading csv. Check logs for more information.', duration=10_000)
            self.logger.error(f'{e}')

    def __panel__(self):
        i_hr = pn.widgets.IntInput.from_param(
            self.param.in_header_row,
        )

        return pn.Column(self.i_if, i_hr)


class StaticDataFrame(InputBlock):
    """ Import static data frame for testing dags.
    
    """

    out_df = param.DataFrame()
    
    def execute(self):
        self.out_df = pd.DataFrame(data = {
            "calories": [420, 380, 390],
            "duration": [50, 40, 45],
            "Latitude": [0, 45, 70],
            "Longitude": [15, 30, 60],
            "Name": ['a', 'b', 'c'],
        })

class ExportDataFrame(Block):
    """ Export a dataframe to a csv.
    
    """

    in_df = param.DataFrame()
    in_file_name = param.String()

    def __init__(self, *args, default_filename='', **kwargs):
        super().__init__(*args, **kwargs)

        self.size_msg = pn.widgets.StaticText(
            value=''
        )
        
        self.i_fn = pn.widgets.TextInput.from_param(
            self.param.in_file_name,
            placeholder='Output file name',
            value=default_filename,
            name=''
        )
        
        self.filedl = pn.widgets.FileDownload(
            file='', 
            button_type='success', 
            filename='',
            label='Download'
        )
        self.filedl.disabled = True

        # Hook up the filename widget to the download widget.
        # Make sure to watch value_input, which is updated live as the user edits the TextInput.
        # 'value' is only updated if the user hits enter.
        #
        def update(event):
            if self.i_fn.value_input:
                self.filedl.disabled = False
                self.filedl.filename = f'{self.i_fn.value_input}.csv'
            else:
                self.filedl.disabled = True
        
        self.i_fn.param.watch(update, 'value_input')

    def execute(self):
        self.size_msg.value = f'Saving data frame of size {self.in_df.shape}. Large files may cause issues.'
        
        sio = StringIO()
        self.in_df.to_csv(sio)
        sio.seek(0)
        self.filedl.file = sio

        # Only allow file download if we've set an input.
        #
        if self.i_fn.value_input:
            self.filedl.disabled = False
        
    def __panel__(self):    
        return pn.Column(
            self.size_msg,
            pn.Row(self.i_fn, pn.widgets.StaticText(value='.csv', name='')),
            self.filedl,
        )

    