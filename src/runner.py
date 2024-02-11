import time
import tkinter as tk
from tkinter import filedialog
from comparator import TableComparator, TableReader

class ExtensionsNotMatchingError(Exception):
    def __init__(self,
                 message="The tables that you specified have different extensions."):
        self.message = message
        super().__init__(self.message)

def retrieve_extension(left_table_path, right_table_path):
    if left_table_path.split(".")[-1] == right_table_path.split(".")[-1]:
        extension = right_table_path.split(".")[-1]
        return extension
    else:
        raise ExtensionsNotMatchingError()

def get_user_input():
    root = tk.Tk()
    root.withdraw()  # Hide the main tkinter window

    print("\nSelect the left table:")
    left_table_path = filedialog.askopenfilename()

    print("\nSelect the right table:")
    right_table_path = filedialog.askopenfilename()

    extension = retrieve_extension(left_table_path, right_table_path)

    if extension in ["csv", "txt"]:
        print("\nSpecify the delimiter.")
        delimiter = input("input: ")
    else:
        delimiter = None

    print("\nSelect the path to save results:")
    result_path = filedialog.askdirectory()

    print("\nProvide the primary keys (comma-separated).")
    primary_keys = input("input: ")

    primary_keys = primary_keys.split(',')

    return left_table_path, right_table_path, extension, delimiter, primary_keys, result_path

def main():
    print("\nWelcome to the table comparator. Please provide your input to run che comparison:")

    while True:
        left_table_path, right_table_path, extension, delimiter, primary_keys, result_path = get_user_input()

        print("\nComparison in progress. Please wait...")
        reader = TableReader(left_table_path=left_table_path, right_table_path=right_table_path, extension=extension, delimiter=delimiter)
        reader.read()
               
        comparator = TableComparator(reader.left_table, reader.right_table, primary_keys=primary_keys, result_path=result_path)

        comparator.prepare_results()
        comparator.visualize_results()
        comparator.return_results()

        print("""\nThe comparison has run successfully. The results are saved in the specifued path.""")

        run_again = input("Do you want to run the program again? (y/n): ").strip().lower()

        if run_again != "y":
            print("\nThank you! The program will close in 5 seconds...")
            time.sleep(5)  # Wait for 5 seconds
            break

if __name__ == "__main__":
    main()