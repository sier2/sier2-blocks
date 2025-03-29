import param
import pandas as pd
import panel as pn
from sier2 import Block

class SimpleTable(Block):
    """ Simple Table Viewer

    Make a tabulator to display an input table.
    """

    in_df = param.DataFrame(doc='Input pandas dataframe')
    out_df = param.DataFrame(doc='Output pandas dataframe', default=pd.DataFrame())

    def execute(self):
        self.out_df = self.in_df

    def __panel__(self):
        return pn.Param(
            self,
            parameters=['out_df'],
            widgets={'out_df': {'type': pn.widgets.Tabulator, 'page_size':20, 'pagination':'local', 'name':'DataFrame'}}
        )

class SimpleTableSelect(Block):
    """ Simple Table Selection

    Make a tabulator to display an input table.
    Pass on selections as an output.
    """

    in_df = param.DataFrame(doc='Input pandas dataframe')
    out_df = param.DataFrame(doc='Output pandas dataframe')

    def __init__(self, *args, block_pause_execution=True, **kwargs):
        super().__init__(*args, block_pause_execution=block_pause_execution, continue_label='Continue With Selection', **kwargs)
        self.tabulator = pn.widgets.Tabulator(pd.DataFrame(), name='DataFrame', page_size=20, pagination='local')

    # def prepare(self):
    #     if self.in_df is not None:
    #         self.tabulator.value = self.in_df
    #     else:
    #         self.tabulator.value = pd.DataFrame()

    def execute(self):
        self.out_df = self.tabulator.selected_dataframe

    def __panel__(self):
        return self.tabulator

class DisplayFilteredTable(Block):
    """
    Display's data and allows the user to filter the columns
    """
    in_df = param.DataFrame(doc='Input pandas dataframe')
    out_data = param.DataFrame(doc='Output pandas dataframe')
    out_cols_sel = param.ListSelector(doc='Select the columns that you wish to have displayed in the table below.')
 
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    @param.depends('out_cols_sel', watch=True)
    def __produce_plot(self):
        if self.out_cols_sel is not None:
            self.out_data = self.in_data[self.out_cols_sel]
            return self.out_data
        else:
            self.out_data = self.in_data
            return self.out_data
            
    def execute(self):
        self.param['out_cols_sel'].objects = self.in_data.columns
        
        #if there are to many columns it creates a lot of latency when panel tries to put it into the tabulator
        if len(self.in_data.columns) >= 20:
            self.out_data = self.in_data.iloc[:,:20]
        else:
            self.out_data = self.in_data
            
    def __panel__(self):
        return pn.Column(
            self.param['out_cols_sel'],
            pn.Param(
                self,
                parameters=['out_data'],
                widgets = {
                    'out_data': {'type': pn.widgets.Tabulator,
                                 'pagination': 'local',
                                 'page_size': 20,
                                 'layout': 'fit_data_table',
                                 'sizing_mode': 'stretch_width'
                                 }
                    }
                ),
            self.__produce_plot())