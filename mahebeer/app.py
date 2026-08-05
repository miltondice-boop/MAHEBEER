from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QPushButton, QDoubleSpinBox, QSpinBox,
    QTabWidget, QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget
)

from .config import APP_NAME, EXPORT_DIR, MEASURES
from .database import Database
from .services import MahebeerService, price_metrics

STYLE = """
QWidget { background:#111827; color:#f9fafb; font-size:14px; }
QLineEdit,QTextEdit,QComboBox,QDoubleSpinBox,QSpinBox { background:#1f2937; border:1px solid #374151; border-radius:8px; padding:8px; }
QPushButton { background:#f59e0b; color:#111827; border:0; border-radius:10px; padding:10px 16px; font-weight:700; }
QPushButton:hover { background:#fbbf24; }
QTableWidget { background:#0b1220; alternate-background-color:#172033; gridline-color:#374151; border:1px solid #374151; }
QHeaderView::section { background:#1f2937; color:#f9fafb; padding:8px; border:0; }
QTabBar::tab { background:#1f2937; padding:12px 18px; border-top-left-radius:8px; border-top-right-radius:8px; }
QTabBar::tab:selected { background:#f59e0b; color:#111827; }
"""

def money(v): return f"${v:,.0f}"

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
        self.load_ingredients();
        if recipe:
            for it in service.recipe_items(recipe["id"]): self.items.append({"ingredient_id":it["ingredient_id"],"name":it["name"],"quantity":it["quantity"],"unit":it["unit"],"unit_cost":it["unit_cost"]})
        self.refresh()
    def load_ingredients(self):
        self.ing.clear()
        for r in self.service.ingredients(self.ing_search.text()): self.ing.addItem(f"{r['name']} ({r['measure_type']}) - {money(r['unit_cost'])}", r)
    def add_item(self):
        r=self.ing.currentData();
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
        buttons=QHBoxLayout();
        for label,fn in [("Nuevo",new),("Editar",edit),("Eliminar",delete),("Duplicar/Copiar receta",self.dup_rec),("Imprimir/Exportar PDF",self.export_pdf)]:
            b=QPushButton(label); b.clicked.connect(fn); buttons.addWidget(b)
        lay=QVBoxLayout(w); lay.addWidget(search); lay.addLayout(buttons); lay.addWidget(table); w.search=search; w.table=table; search.textChanged.connect(self.refresh_all); return w
    def selected_id(self, table):
        row=table.currentRow(); return int(table.item(row,0).text()) if row>=0 and table.item(row,0) else None
    def new_ing(self):
        d=IngredientDialog(self); 
        if d.exec(): self.service.add_ingredient(d.name.text(),d.cost.value(),d.qty.value(),d.measure.currentText()); self.refresh_all()
    def edit_ing(self):
        iid=self.selected_id(self.ing_tab.table); rows=[r for r in self.service.ingredients(include_deleted=True) if r["id"]==iid]
        if rows:
            d=IngredientDialog(self,rows[0]);
            if d.exec(): self.service.update_ingredient(iid,d.name.text(),d.cost.value(),d.qty.value(),d.measure.currentText()); self.refresh_all()
    def del_ing(self):
        iid=self.selected_id(self.ing_tab.table); 
        if iid: self.service.soft_delete_ingredient(iid); self.refresh_all()
    def new_rec(self): self.recipe_dialog(None)
    def edit_rec(self):
        rid=self.selected_id(self.rec_tab.table); rows=[r for r in self.service.recipes(include_deleted=True) if r["id"]==rid]
        if rows: self.recipe_dialog(rows[0])
    def recipe_dialog(self, recipe):
        d=RecipeDialog(self.service,self,recipe)
        if d.exec():
            self.service.save_recipe(recipe["id"] if recipe else None,d.name.text(),d.desc.toPlainText(),d.portions.value(),d.margin.value(),d.manual.value(),d.items); self.refresh_all()
    def del_rec(self):
        rid=self.selected_id(self.rec_tab.table); 
        if rid: self.service.soft_delete_recipe(rid); self.refresh_all()
    def dup_rec(self):
        rid=self.selected_id(self.rec_tab.table)
        if rid: self.service.duplicate_recipe(rid); self.refresh_all()
    def refresh_all(self):
        self.fill_ingredients(); self.fill_recipes(); self.fill_reports(); self.fill_trash()
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
    def export_excel(self): self.service.export_excel(EXPORT_DIR/"mahebeer_reporte.xlsx"); QMessageBox.information(self,"Exportado",str(EXPORT_DIR/"mahebeer_reporte.xlsx"))
    def export_pdf(self): self.service.export_pdf(EXPORT_DIR/"mahebeer_reporte.pdf"); QMessageBox.information(self,"Exportado",str(EXPORT_DIR/"mahebeer_reporte.pdf"))
    def import_excel(self):
        path,_=QFileDialog.getOpenFileName(self,"Importar Excel",str(Path.home()),"Excel (*.xlsx)")
        if path: QMessageBox.information(self,"Importación",f"Ingredientes importados: {self.service.import_ingredients_excel(Path(path))}"); self.refresh_all()

def main():
    app=QApplication(sys.argv); app.setStyleSheet(STYLE); w=MainWindow(); w.show(); sys.exit(app.exec())

if __name__ == "__main__": main()
