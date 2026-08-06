from __future__ import annotations

import os
import sys
from pathlib import Path

from .config import APP_NAME, EXPORT_DIR, MEASURES
from .database import Database
from .services import MahebeerService, price_metrics

try:
    from PySide6.QtGui import QAction
    from PySide6.QtWidgets import QApplication, QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton, QDoubleSpinBox, QTabWidget, QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget
    HAS_QT = True
except ImportError:
    HAS_QT = False

STYLE = """
QWidget { background:#111827; color:#f9fafb; font-size:14px; }
QLineEdit,QTextEdit,QComboBox,QDoubleSpinBox { background:#1f2937; border:1px solid #374151; border-radius:8px; padding:8px; }
QPushButton { background:#f59e0b; color:#111827; border:0; border-radius:10px; padding:10px 16px; font-weight:700; }
QPushButton:hover { background:#fbbf24; }
QTableWidget { background:#0b1220; alternate-background-color:#172033; gridline-color:#374151; border:1px solid #374151; }
QHeaderView::section { background:#1f2937; color:#f9fafb; padding:8px; border:0; }
QTabBar::tab { background:#1f2937; padding:12px 18px; border-top-left-radius:8px; border-top-right-radius:8px; }
QTabBar::tab:selected { background:#f59e0b; color:#111827; }
"""

def money(v: float) -> str:
    return f"${v:,.0f}"

if HAS_QT:
    class IngredientDialog(QDialog):
        def __init__(self, parent=None, row=None):
            super().__init__(parent); self.setWindowTitle("Ingrediente")
            self.name=QLineEdit(row["name"] if row else "")
            self.cost=QDoubleSpinBox(); self.cost.setMaximum(999999999); self.cost.setValue(row["purchase_cost"] if row else 0)
            self.qty=QDoubleSpinBox(); self.qty.setMaximum(999999999); self.qty.setValue(row["purchased_quantity"] if row else 1)
            self.measure=QComboBox(); self.measure.addItems(MEASURES); self.measure.setCurrentText(row["measure_type"] if row else MEASURES[0])
            self.preview=QLabel(); self.cost.valueChanged.connect(self.update_preview); self.qty.valueChanged.connect(self.update_preview); self.measure.currentTextChanged.connect(self.update_preview)
            save=QPushButton("Guardar"); save.clicked.connect(self.accept)
            form=QFormLayout(self); form.addRow("Nombre",self.name); form.addRow("Costo de compra",self.cost); form.addRow("Cantidad comprada",self.qty); form.addRow("Tipo de medida",self.measure); form.addRow("Costo unitario",self.preview); form.addRow(save); self.update_preview()
        def update_preview(self):
            label = {"Gramos":"gramo","Mililitros":"mililitro","Unidades":"unidad"}[self.measure.currentText()]
            self.preview.setText(f"{money(self.cost.value()/max(self.qty.value(),0.0001))} por {label}")

    class RecipeDialog(QDialog):
        def __init__(self, service, parent=None, recipe=None):
            super().__init__(parent); self.service=service; self.recipe=recipe; self.items=[]; self.setWindowTitle("Receta"); self.resize(900,650)
            self.name=QLineEdit(recipe["name"] if recipe else ""); self.desc=QTextEdit(recipe["description"] if recipe else "")
            self.portions=QDoubleSpinBox(); self.portions.setMaximum(99999); self.portions.setValue(recipe["yield_portions"] if recipe else 1)
            self.margin=QDoubleSpinBox(); self.margin.setMaximum(1000); self.margin.setSuffix(" %"); self.margin.setValue(recipe["suggested_margin"] if recipe else 30)
            self.manual=QDoubleSpinBox(); self.manual.setMaximum(999999999); self.manual.setValue(recipe["manual_sale_price"] if recipe else 0)
            self.ing_search=QLineEdit(); self.ing_search.setPlaceholderText("Buscar ingrediente: pollo, arroz, sal...")
            self.ing=QComboBox(); self.qty=QDoubleSpinBox(); self.qty.setMaximum(999999); self.qty.setValue(1)
            self.table=QTableWidget(0,4); self.table.setHorizontalHeaderLabels(["Ingrediente","Cantidad","Unidad","Costo"])
            self.summary=QLabel(); add=QPushButton("Agregar ingrediente"); add.clicked.connect(self.add_item); save=QPushButton("Guardar receta"); save.clicked.connect(self.accept)
            self.ing_search.textChanged.connect(self.load_ingredients); self.portions.valueChanged.connect(self.refresh); self.margin.valueChanged.connect(self.refresh); self.manual.valueChanged.connect(self.refresh)
            form=QFormLayout(); form.addRow("Nombre del producto",self.name); form.addRow("Descripción",self.desc); form.addRow("Rendimiento / porciones",self.portions); form.addRow("Margen de utilidad",self.margin); form.addRow("Precio de venta manual (0 = sugerido)",self.manual)
            top=QHBoxLayout(); top.addWidget(self.ing_search); top.addWidget(self.ing); top.addWidget(QLabel("Cantidad")); top.addWidget(self.qty); top.addWidget(add)
            lay=QVBoxLayout(self); lay.addLayout(form); lay.addLayout(top); lay.addWidget(self.table); lay.addWidget(self.summary); lay.addWidget(save)
            self.load_ingredients()
            if recipe:
                for it in service.recipe_items(recipe["id"]): self.items.append({"ingredient_id":it["ingredient_id"],"name":it["name"],"quantity":it["quantity"],"unit":it["unit"],"unit_cost":it["unit_cost"]})
            self.refresh()
        def load_ingredients(self):
            self.ing.clear()
            for r in self.service.ingredients(self.ing_search.text()):
                self.ing.addItem(f"{r['name']} ({r['measure_type']}) - {money(r['unit_cost'])}", dict(r))
        def add_item(self):
            r=self.ing.currentData()
            if r: self.items.append({"ingredient_id":r["id"],"name":r["name"],"quantity":self.qty.value(),"unit":r["measure_type"],"unit_cost":r["unit_cost"]}); self.refresh()
        def refresh(self):
            self.table.setRowCount(0); total=0
            for it in self.items:
                cost=it["quantity"]*it["unit_cost"]; total+=cost; row=self.table.rowCount(); self.table.insertRow(row)
                for col,val in enumerate([it["name"], it["quantity"], it["unit"], money(cost)]): self.table.setItem(row,col,QTableWidgetItem(str(val)))
            m=price_metrics(total,self.portions.value(),self.margin.value(),self.manual.value())
            self.summary.setText(f"Costo total: {money(m.total_cost)} | Costo por porción: {money(m.cost_per_portion)} | Precio sugerido: {money(m.suggested_price)} | Ganancia: {money(m.profit_value)} ({m.profit_percent:.1f}%) | Margen bruto: {m.gross_margin:.1f}% | Rentabilidad: {m.profitability:.2f}x")

    class MainWindow(QMainWindow):
        def __init__(self):
            super().__init__(); self.db=Database(); self.service=MahebeerService(self.db); self.setWindowTitle(APP_NAME); self.resize(1200,760)
            tabs=QTabWidget(); self.setCentralWidget(tabs)
            self.ing_tab=self.make_list_tab("Buscar ingredientes...", ["ID","Nombre","Compra","Cantidad","Medida","Costo unitario"], self.new_ing, self.edit_ing, self.del_ing); tabs.addTab(self.ing_tab,"Ingredientes")
            self.rec_tab=self.make_list_tab("Buscar recetas...", ["ID","Nombre","Rendimiento","Costo total","Precio sugerido","Margen bruto"], self.new_rec, self.edit_rec, self.del_rec); tabs.addTab(self.rec_tab,"Recetas y costos")
            self.reports=QTextEdit(); self.reports.setReadOnly(True); tabs.addTab(self.reports,"Reportes / Historial")
            self.trash=QTableWidget(0,4); self.trash.setHorizontalHeaderLabels(["Tipo","ID","Nombre","Eliminado"]); tabs.addTab(self.trash,"Papelera")
            menu=self.menuBar().addMenu("Archivo")
            for text, fn in [("Exportar Excel",self.export_excel),("Exportar PDF",self.export_pdf),("Importar ingredientes Excel",self.import_excel),("Crear copia de seguridad",lambda:self.db.backup())]:
                a=QAction(text,self); a.triggered.connect(fn); menu.addAction(a)
            self.refresh_all()
        def make_list_tab(self, placeholder, headers, new, edit, delete):
            w=QWidget(); search=QLineEdit(); search.setPlaceholderText(placeholder); table=QTableWidget(0,len(headers)); table.setHorizontalHeaderLabels(headers); table.setAlternatingRowColors(True)
            buttons=QHBoxLayout()
            for label,fn in [("Nuevo",new),("Editar",edit),("Eliminar",delete),("Duplicar/Copiar receta",self.dup_rec),("Imprimir/Exportar PDF",self.export_pdf)]:
                b=QPushButton(label); b.clicked.connect(fn); buttons.addWidget(b)
            lay=QVBoxLayout(w); lay.addWidget(search); lay.addLayout(buttons); lay.addWidget(table); w.search=search; w.table=table; search.textChanged.connect(self.refresh_all); return w
        def selected_id(self, table):
            row=table.currentRow(); return int(table.item(row,0).text()) if row>=0 and table.item(row,0) else None
        def new_ing(self):
            d=IngredientDialog(self)
            if d.exec(): self.service.add_ingredient(d.name.text(),d.cost.value(),d.qty.value(),d.measure.currentText()); self.refresh_all()
        def edit_ing(self):
            iid=self.selected_id(self.ing_tab.table); rows=[r for r in self.service.ingredients(include_deleted=True) if r["id"]==iid]
            if rows:
                d=IngredientDialog(self,rows[0])
                if d.exec(): self.service.update_ingredient(iid,d.name.text(),d.cost.value(),d.qty.value(),d.measure.currentText()); self.refresh_all()
        def del_ing(self):
            iid=self.selected_id(self.ing_tab.table)
            if iid: self.service.soft_delete_ingredient(iid); self.refresh_all()
        def new_rec(self): self.recipe_dialog(None)
        def edit_rec(self):
            rid=self.selected_id(self.rec_tab.table); rows=[r for r in self.service.recipes(include_deleted=True) if r["id"]==rid]
            if rows: self.recipe_dialog(rows[0])
        def recipe_dialog(self, recipe):
            d=RecipeDialog(self.service,self,recipe)
            if d.exec():
                if not d.name.text().strip():
                    QMessageBox.warning(self, "Validación", "Escriba el nombre de la receta")
                    return
                if not d.items:
                    QMessageBox.warning(self, "Validación", "Busque y agregue al menos un ingrediente")
                    return
                self.service.save_recipe(recipe["id"] if recipe else None,d.name.text(),d.desc.toPlainText(),d.portions.value(),d.margin.value(),d.manual.value(),d.items); self.refresh_all()
        def del_rec(self):
            rid=self.selected_id(self.rec_tab.table)
            if rid: self.service.soft_delete_recipe(rid); self.refresh_all()
        def dup_rec(self):
            rid=self.selected_id(self.rec_tab.table)
            if rid: self.service.duplicate_recipe(rid); self.refresh_all()
        def refresh_all(self): self.fill_ingredients(); self.fill_recipes(); self.fill_reports(); self.fill_trash()
        def fill_ingredients(self):
            t=self.ing_tab.table; t.setRowCount(0)
            for r in self.service.ingredients(self.ing_tab.search.text()):
                row=t.rowCount(); t.insertRow(row)
                for c,v in enumerate([r["id"],r["name"],money(r["purchase_cost"]),r["purchased_quantity"],r["measure_type"],money(r["unit_cost"])]): t.setItem(row,c,QTableWidgetItem(str(v)))
        def fill_recipes(self):
            t=self.rec_tab.table; t.setRowCount(0)
            for r in self.service.recipes(self.rec_tab.search.text()):
                m=price_metrics(r["total_cost"],r["yield_portions"],r["suggested_margin"],r["manual_sale_price"]); row=t.rowCount(); t.insertRow(row)
                for c,v in enumerate([r["id"],r["name"],r["yield_portions"],money(m.total_cost),money(m.suggested_price),f"{m.gross_margin:.1f}%"]): t.setItem(row,c,QTableWidgetItem(str(v)))
        def fill_reports(self):
            d=self.service.dashboard_reports(); lines=["INGREDIENTES MÁS COSTOSOS"]+[f"- {r['name']}: {money(r['unit_cost'])}" for r in d['expensive']]
            lines += ["", f"Valor total del inventario: {money(d['inventory'])}", f"Costo promedio por receta: {money(d['avg_cost'])}", "", "HISTORIAL DE CAMBIOS"]
            lines += [f"{h['created_at']} | {h['entity']} #{h['entity_id']} | {h['action']} | {h['details']}" for h in d['history']]
            self.reports.setPlainText("\n".join(lines))
        def fill_trash(self):
            self.trash.setRowCount(0)
            for kind, rows in (("Ingrediente", self.service.ingredients(include_deleted=True)), ("Receta", self.service.recipes(include_deleted=True))):
                for r in rows:
                    if r["deleted_at"]:
                        row=self.trash.rowCount(); self.trash.insertRow(row)
                        for c,v in enumerate([kind,r["id"],r["name"],r["deleted_at"]]): self.trash.setItem(row,c,QTableWidgetItem(str(v)))
        def export_excel(self):
            path=self.service.export_excel(EXPORT_DIR/"mahebeer_reporte.xlsx"); QMessageBox.information(self,"Exportado",str(path))
        def export_pdf(self):
            path=self.service.export_pdf(EXPORT_DIR/"mahebeer_reporte.pdf"); QMessageBox.information(self,"Exportado",str(path))
        def import_excel(self):
            path,_=QFileDialog.getOpenFileName(self,"Importar Excel",str(Path.home()),"Excel (*.xlsx)")
            if path: QMessageBox.information(self,"Importación",f"Ingredientes importados: {self.service.import_ingredients_excel(Path(path))}"); self.refresh_all()

def _main_qt() -> None:
    app=QApplication(sys.argv); app.setStyleSheet(STYLE); w=MainWindow(); w.show(); sys.exit(app.exec())

def _main_tk() -> None:
    import tkinter as tk
    from tkinter import ttk, messagebox

    db = Database()
    service = MahebeerService(db)
    root = tk.Tk()
    root.title(APP_NAME)
    root.geometry("1180x760")
    root.configure(bg="#111827")
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("TFrame", background="#111827")
    style.configure("TLabel", background="#111827", foreground="#f9fafb")
    style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=8)
    style.configure("Treeview", background="#0b1220", foreground="#f9fafb", fieldbackground="#0b1220")

    book = ttk.Notebook(root)
    book.pack(fill="both", expand=True, padx=12, pady=12)
    ing_frame = ttk.Frame(book)
    rec_frame = ttk.Frame(book)
    rep_frame = ttk.Frame(book)
    book.add(ing_frame, text="Ingredientes")
    book.add(rec_frame, text="Recetas y costos")
    book.add(rep_frame, text="Reportes")

    def tree(parent, cols):
        tv = ttk.Treeview(parent, columns=cols, show="headings", height=15)
        for c in cols:
            tv.heading(c, text=c)
            tv.column(c, width=140)
        tv.pack(fill="both", expand=True, pady=8)
        return tv

    search_i = tk.StringVar()
    ttk.Entry(ing_frame, textvariable=search_i).pack(fill="x", padx=8, pady=8)
    ing_tree = tree(ing_frame, ("ID", "Nombre", "Compra", "Cantidad", "Medida", "Costo unitario"))
    search_r = tk.StringVar()
    ttk.Entry(rec_frame, textvariable=search_r).pack(fill="x", padx=8, pady=8)
    rec_tree = tree(rec_frame, ("ID", "Nombre", "Rendimiento", "Costo total", "Precio sugerido", "Margen bruto"))
    report = tk.Text(rep_frame, bg="#0b1220", fg="#f9fafb", insertbackground="#f9fafb")
    report.pack(fill="both", expand=True, padx=8, pady=8)

    def refresh(*_):
        ing_tree.delete(*ing_tree.get_children())
        rec_tree.delete(*rec_tree.get_children())
        report.delete("1.0", "end")
        for r in service.ingredients(search_i.get()):
            ing_tree.insert("", "end", values=(r["id"], r["name"], money(r["purchase_cost"]), r["purchased_quantity"], r["measure_type"], money(r["unit_cost"])))
        for r in service.recipes(search_r.get()):
            m = price_metrics(r["total_cost"], r["yield_portions"], r["suggested_margin"], r["manual_sale_price"])
            rec_tree.insert("", "end", values=(r["id"], r["name"], r["yield_portions"], money(m.total_cost), money(m.suggested_price), f"{m.gross_margin:.1f}%"))
        d = service.dashboard_reports()
        report.insert("end", f"Valor total inventario: {money(d['inventory'])}\nCosto promedio: {money(d['avg_cost'])}\n\nIngredientes más costosos:\n")
        for r in d["expensive"]:
            report.insert("end", f"- {r['name']}: {money(r['unit_cost'])}\n")

    def add_ingredient_dialog():
        win = tk.Toplevel(root)
        win.title("Nuevo ingrediente")
        win.configure(bg="#111827")
        name = tk.StringVar()
        cost = tk.DoubleVar(value=0)
        qty = tk.DoubleVar(value=1)
        measure = tk.StringVar(value=MEASURES[0])
        fields = ttk.Frame(win)
        fields.pack(padx=16, pady=16, fill="x")
        for label, widget in (
            ("Nombre", ttk.Entry(fields, textvariable=name)),
            ("Costo de compra", ttk.Entry(fields, textvariable=cost)),
            ("Cantidad comprada", ttk.Entry(fields, textvariable=qty)),
            ("Medida", ttk.Combobox(fields, textvariable=measure, values=MEASURES, state="readonly")),
        ):
            ttk.Label(fields, text=label).pack(anchor="w")
            widget.pack(fill="x", pady=(0, 8))
        def save():
            if not name.get().strip():
                messagebox.showerror("Validación", "Escriba el nombre del ingrediente")
                return
            service.add_ingredient(name.get(), float(cost.get()), float(qty.get()), measure.get())
            win.destroy()
            refresh()
        ttk.Button(fields, text="Guardar ingrediente", command=save).pack(fill="x", pady=8)

    def add_recipe_dialog():
        win = tk.Toplevel(root)
        win.title("Nueva receta")
        win.geometry("900x650")
        win.configure(bg="#111827")
        selected_items = []
        name = tk.StringVar()
        portions = tk.DoubleVar(value=1)
        margin = tk.DoubleVar(value=30)
        manual = tk.DoubleVar(value=0)
        ingredient_search = tk.StringVar()
        ingredient_qty = tk.DoubleVar(value=1)
        top = ttk.Frame(win)
        top.pack(fill="x", padx=12, pady=12)
        for label, var in (("Nombre del producto", name), ("Rendimiento / porciones", portions), ("Margen %", margin), ("Precio manual (0=sugerido)", manual)):
            ttk.Label(top, text=label).pack(anchor="w")
            ttk.Entry(top, textvariable=var).pack(fill="x", pady=(0, 6))
        ttk.Label(top, text="Descripción").pack(anchor="w")
        desc = tk.Text(top, height=3, bg="#0b1220", fg="#f9fafb", insertbackground="#f9fafb")
        desc.pack(fill="x", pady=(0, 8))

        chooser = ttk.Frame(win)
        chooser.pack(fill="x", padx=12)
        ttk.Label(chooser, text="Buscar ingrediente para agregar a la receta").grid(row=0, column=0, sticky="w")
        ttk.Entry(chooser, textvariable=ingredient_search).grid(row=1, column=0, sticky="ew", padx=(0, 8))
        ttk.Label(chooser, text="Cantidad usada").grid(row=0, column=1, sticky="w")
        ttk.Entry(chooser, textvariable=ingredient_qty, width=14).grid(row=1, column=1, padx=(0, 8))
        chooser.columnconfigure(0, weight=1)
        match_tree = ttk.Treeview(win, columns=("ID", "Nombre", "Medida", "Costo unitario"), show="headings", height=6)
        for col in ("ID", "Nombre", "Medida", "Costo unitario"):
            match_tree.heading(col, text=col)
            match_tree.column(col, width=140)
        match_tree.pack(fill="x", padx=12, pady=8)
        items_tree = ttk.Treeview(win, columns=("ID", "Ingrediente", "Cantidad", "Unidad", "Costo"), show="headings", height=8)
        for col in ("ID", "Ingrediente", "Cantidad", "Unidad", "Costo"):
            items_tree.heading(col, text=col)
            items_tree.column(col, width=140)
        items_tree.pack(fill="both", expand=True, padx=12, pady=8)
        summary = ttk.Label(win, text="Costo total: $0")
        summary.pack(fill="x", padx=12, pady=4)

        def load_matches(*_):
            match_tree.delete(*match_tree.get_children())
            for r in service.ingredients(ingredient_search.get()):
                match_tree.insert("", "end", values=(r["id"], r["name"], r["measure_type"], money(r["unit_cost"])))
        def update_items():
            items_tree.delete(*items_tree.get_children())
            total = 0.0
            for item in selected_items:
                cost = item["quantity"] * item["unit_cost"]
                total += cost
                items_tree.insert("", "end", values=(item["ingredient_id"], item["name"], item["quantity"], item["unit"], money(cost)))
            m = price_metrics(total, float(portions.get() or 1), float(margin.get() or 0), float(manual.get() or 0))
            summary.config(text=f"Costo total: {money(m.total_cost)} | Porción: {money(m.cost_per_portion)} | Precio sugerido: {money(m.suggested_price)} | Ganancia: {money(m.profit_value)} | Margen bruto: {m.gross_margin:.1f}%")
        def add_selected_ingredient():
            selection = match_tree.selection()
            if not selection:
                messagebox.showerror("Validación", "Busque y seleccione un ingrediente")
                return
            iid = int(match_tree.item(selection[0], "values")[0])
            rows = [r for r in service.ingredients(include_deleted=False) if r["id"] == iid]
            if not rows:
                return
            r = rows[0]
            selected_items.append({"ingredient_id": r["id"], "name": r["name"], "quantity": float(ingredient_qty.get()), "unit": r["measure_type"], "unit_cost": r["unit_cost"]})
            update_items()
        def save_recipe():
            if not name.get().strip():
                messagebox.showerror("Validación", "Escriba el nombre de la receta")
                return
            if not selected_items:
                messagebox.showerror("Validación", "Agregue al menos un ingrediente")
                return
            service.save_recipe(None, name.get(), desc.get("1.0", "end").strip(), float(portions.get()), float(margin.get()), float(manual.get()), selected_items)
            win.destroy()
            refresh()
        ttk.Button(chooser, text="Agregar ingrediente", command=add_selected_ingredient).grid(row=1, column=2)
        ttk.Button(win, text="Guardar receta", command=save_recipe).pack(fill="x", padx=12, pady=8)
        ingredient_search.trace_add("write", load_matches)
        portions.trace_add("write", lambda *_: update_items())
        margin.trace_add("write", lambda *_: update_items())
        manual.trace_add("write", lambda *_: update_items())
        load_matches()

    buttons_i = ttk.Frame(ing_frame)
    buttons_i.pack(fill="x", padx=8)
    ttk.Button(buttons_i, text="Nuevo ingrediente", command=add_ingredient_dialog).pack(side="left", padx=4)
    buttons_r = ttk.Frame(rec_frame)
    buttons_r.pack(fill="x", padx=8)
    ttk.Button(buttons_r, text="Nueva receta con buscador de ingredientes", command=add_recipe_dialog).pack(side="left", padx=4)
    search_i.trace_add("write", refresh)
    search_r.trace_add("write", refresh)
    refresh()
    root.mainloop()

def _headless_check() -> None:
    db = Database()
    service = MahebeerService(db)
    print(f"{APP_NAME} inicializada en modo verificación sin pantalla.")
    print(f"Ingredientes: {len(service.ingredients())}")
    print(f"Recetas: {len(service.recipes())}")
    print("En Windows ejecute: python -m mahebeer.app")

def main() -> None:
    if sys.platform != "win32" and not os.environ.get("DISPLAY"):
        _headless_check()
        return
    if HAS_QT:
        _main_qt()
    else:
        _main_tk()

if __name__ == "__main__":
    main()
