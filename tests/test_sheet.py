from wizard import Sheet, Cell, Book
import pandas as pd


class TestSheet:
    def test_getitem_single(self, sheet: Sheet):
        a1 = sheet["A1"]  # column - row
        a1_2 = sheet[1, 1]  # row - column
        assert a1 == a1_2
        assert a1.row == 1 and a1.column == 1

    def test_getitem_single_row(self, sheet: Sheet):
        row1 = sheet[1]
        assert len(row1) == sheet.ncols
        assert row1.iloc[0].row == 1 and row1.iloc[0].column == 1

    def test_getitem_single_column(self, sheet: Sheet):
        col1 = sheet["A"]
        assert len(col1) == sheet.nrows
        assert col1.iloc[0].row == 1 and col1.iloc[0].column == 1

    def test_getitem_multiple_rows(self, sheet: Sheet):
        rows = sheet[1:3]
        assert len(rows) == 2
        assert rows.iloc[0, 0].row == 1 and rows.iloc[0, 0].column == 1
        assert rows.iloc[-1, -1].row == 2 and rows.iloc[-1, -1].column == sheet.ncols

    def test_getitem_multiple_columns(self, sheet: Sheet):
        cols = sheet[:, 1:3]
        assert len(cols) == sheet.nrows
        assert len(cols.iloc[0]) == 2
        assert cols.iloc[0, 0].row == 1 and cols.iloc[0, 0].column == 1
        assert cols.iloc[-1, -1].row == sheet.nrows and cols.iloc[-1, -1].column == 2

    def test_getitem_multiple_rows_colmuns(self, sheet: Sheet):
        subset = sheet[2, 1:3]
        assert len(subset) == 2
        assert subset.iloc[0].row == 2 and subset.iloc[0].column == 1
        assert subset.iloc[-1].row == 2 and subset.iloc[-1].column == 2

    def test_gsheet(self):
        data = [
            ["Hello", "Hello"],
            ["1", 1],
            ["True", True],
        ]
        df = pd.DataFrame(
            map(lambda row: [Cell(value=col) for col in row], data), columns=[0, 1]
        )
        sheet = Sheet(title="test", sheet=df)
        book = sheet.to_book()
        id = book.to_gsheet()

        book1 = Book.from_gsheet(id)
        sheet1 = book1.sheets["test"]
        assert sheet1.nrows == len(data)
        assert sheet1.ncols == len(data[0])
