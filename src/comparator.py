import pandas as pd
import plotly.express as px
import os

class InconsistentDataTypesError(Exception):
    def __init__(self,
                 inconsistent_dict):
        inconsistent_string = ("\n".join(
            f"""Column name: {key}
            - left_table: {value['left_table']}
            - right_table: {value['right_table']}"""
            for key, value in inconsistent_dict.items()))
        
        self.message = f"\nThe following columns have inconsistent data types:\n{inconsistent_string}"
        
        super().__init__(self.message)


class TableReader():
    def __init__(self,
                 left_table_path,
                 right_table_path,
                 extension,
                 delimiter:str = None):
        self.left_table_path = left_table_path
        self.right_table_path = right_table_path
        self.extension = extension
        self.delimiter = delimiter
    
    def read(self):
        if self.extension == "xlsx":
            self.left_table = pd.read_excel(self.left_table_path)
            self.right_table = pd.read_excel(self.right_table_path)
        if self.extension in ["csv", "txt"]:
            self.left_table = pd.read_csv(self.left_table_path, delimiter=self.delimiter)
            self.right_table = pd.read_csv(self.right_table_path, delimiter=self.delimiter)
        

class TableComparator():
    def __init__(self,
                 left_table,
                 right_table,
                 primary_keys,
                 result_path,
                 delimiter:str = None):
        self.left_table = left_table
        self.right_table = right_table
        self.delimiter = delimiter
        self.primary_keys = primary_keys
        self.result_path = result_path

    def validate_data_quality(self):
        assert len(self.left_table.columns) == len(self.right_table.columns), "The tables must have the same number of columns."
        assert all(self.left_table.columns == self.right_table.columns), "Columns names are inconsistent."
        if all(self.left_table.dtypes == self.right_table.dtypes) == False:
            left_inconsistent_dict = self.right_table.dtypes[(self.left_table.dtypes == self.right_table.dtypes) == False].to_dict()
            right_inconsistent_dict = self.left_table.dtypes[(self.left_table.dtypes == self.right_table.dtypes) == False].to_dict()

            inconsistent_dict = {}
            for key, value in left_inconsistent_dict.items():
                inconsistent_dict[key] = {"left_table": left_inconsistent_dict[key].type,
                                        "right_table": right_inconsistent_dict[key].type}
            raise InconsistentDataTypesError(inconsistent_dict)
        assert all(self.left_table.duplicated(subset = self.primary_keys) == False), "The left table contains duplicates."
        assert all(self.right_table.duplicated(subset = self.primary_keys) == False), "The right table contains duplicates."


    def join_tables(self):
        self.joined = (self.left_table
                       .merge(self.right_table,
                              on = self.primary_keys,
                              indicator=True,
                              suffixes=["_left_table", "_right_table"],
                              how = "outer"))

    def split_joined_table(self):
        # In the left table but not in the right table
        left_only =  self.joined[self.joined["_merge"] == "left_only"].copy(deep = True)
        columns = self.primary_keys + [column_name for column_name in left_only.columns if "_left_table" in column_name]
        left_only = left_only[columns]
        left_only.columns = [column.replace("_left_table","") for column in left_only.columns]
        self.left_only = left_only

        # In the right table but not in the left table
        right_only =  self.joined[self.joined["_merge"] == "right_only"].copy(deep = True)
        columns = self.primary_keys + [column_name for column_name in right_only.columns if "_right_table" in column_name]
        right_only = right_only[columns]
        right_only.columns = [column.replace("_right_table","") for column in right_only.columns]
        self.right_only = right_only

        # In both tables
        self.both = self.joined[self.joined["_merge"] == "both"].copy(deep = True)

    def compare_records_in_both(self):
        left_columns = self.primary_keys + [column_name for column_name in self.both.columns if "_left_table" in column_name]
        right_columns = self.primary_keys + [column_name for column_name in self.both.columns if "_right_table" in column_name]

        both = self.both[[column for column in self.both.columns if column != "_merge"]].copy()
        both.fillna("", inplace=True)

        comparison_df_list = []
        for index, row in both.iterrows():
            left_row = row[left_columns].reset_index(drop=True)
            right_row = row[right_columns].reset_index(drop=True)
            
            comparison_rows = pd.DataFrame([left_row,
                                            right_row,
                                            left_row==right_row])
            comparison_rows["comparison"] = ["left_table", "right_table", "comparison_result"]
            comparison_df_list.append(comparison_rows)

        comparison_df = pd.concat(comparison_df_list)
        comparison_df.columns = list(self.left_table.columns) + ["comparison"]
        comparison_df = comparison_df[["comparison"] + list(self.left_table.columns)]
        self.comparison_df = comparison_df.reset_index(drop=True, inplace=False)

    def prepare_results(self):
        self.validate_data_quality()
        self.join_tables()
        self.split_joined_table()
        self.compare_records_in_both()

    def visualize_record_availability(self):
        merge_counts = self.joined['_merge'].value_counts()
        merge_counts_df = pd.DataFrame({'_merge': merge_counts.index, 'count': merge_counts.values})
        merge_counts_df['percentage'] = (merge_counts_df['count'] / merge_counts_df['count'].sum()) * 100

        merge_counts_df['_merge'].replace({'left_only': 'Tylko w lewej', 'right_only': 'Tylko w prawej', 'both': 'W obu'}, inplace=True)

        fig = px.pie(merge_counts_df, names='_merge', values='percentage', title='Dostępność danych w tabelach.')

        fig.update_layout(
            autosize=False,
            width=500,
            height=500,
            margin=dict(l=30, r=30, t=40, b=0),
            legend=dict(orientation="h", x=0.12, y=-0),
            title=dict(x=0.5, y=0.97))

        self.record_availability = fig

    def visualize_record_consistency(self):
        comparison_result = self.comparison_df[self.comparison_df["comparison"]=="comparison_result"]

        columns = [column for column in comparison_result.columns if column not in ["comparison"] + self.primary_keys] 

        records_consistency = {}
        for column in columns:
            records_consistency[column] = (comparison_result[comparison_result[column] == True].shape[0]/comparison_result.shape[0])

        # Convert the dictionary to a DataFrame
        df = pd.DataFrame({'Column': list(records_consistency.keys()), 'Percentage': [value * 100 for value in records_consistency.values()]})

        fig = px.bar(df, x='Column', y='Percentage', text='Percentage', title='Zgodność wartości według kolumn (w %)')

        # Customize the layout if needed
        fig.update_traces(texttemplate='%{text:.2f}%', textposition='inside')
        fig.update_xaxes(title_text='Kolumna')
        fig.update_yaxes(title_text='Odsetek wartości zgodnych')

        self.record_consistency = fig
    
    def visualize_results(self):
        self.visualize_record_availability()
        self.visualize_record_consistency()

    def return_results(self):
        self.record_availability.write_image(os.path.join(self.result_path,"record_availability.png"))
        self.record_consistency.write_image(os.path.join(self.result_path,"record_consistency.png"))

        self.left_only.to_excel(os.path.join(self.result_path,"left_only.xlsx"), index=False)
        self.right_only.to_excel(os.path.join(self.result_path,"right_only.xlsx"), index=False)
        self.comparison_df.to_excel(os.path.join(self.result_path,"comparison_df.xlsx"), index=False)
