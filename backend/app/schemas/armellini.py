from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class ResumenImportacion(BaseModel):
    archivo: str
    total_cajas: int
    total_tallos: int
    awbs: list[str]
    hawbs: list[str]
    facturas: list[int]
    carriers: list[str]
    cajas_sin_po: int
    insertadas: int
    actualizadas: int
    avisos: list[str] = []
    conciliacion: list[dict] = []


class CajaArmellini(BaseModel):
    codigo_pieza: str
    awb: str
    factura: Optional[int] = None      # pedido (asi lo nombra mal el XML de operaciones)
    invoice: Optional[int] = None      # dartis_ventas.id_comercializadora -> <Invoice>
    po: Optional[str] = None
    nombre_cliente: str = ""
    consignee_code: Optional[str] = None
    farm_name: Optional[str] = None
    product_code: Optional[str] = None
    descripcion_producto: str = ""
    largo_inch: Optional[int] = None
    ancho_inch: Optional[int] = None
    alto_inch: Optional[int] = None
    carrier_miami: Optional[str] = None
    fecha_carrier: Optional[date] = None


class PreviewOut(BaseModel):
    total_cajas: int
    shipdate_sugerido: Optional[date] = None
    avisos: list[str] = []
    cajas: list[CajaArmellini] = []


class POAsignado(BaseModel):
    codigo_pieza: str
    po: str = Field(min_length=1, max_length=64)


class GenerarIn(BaseModel):
    barcodes: list[str] = Field(min_length=1, description="Cajas a incluir en el XML")
    shipdate: date
    shipper: Optional[str] = Field(default=None, max_length=32)
    pos: list[POAsignado] = Field(default=[], description="PO digitado para las cajas que llegaron sin el")


class GenerarOut(BaseModel):
    export_id: int
    filename: str
    total_cajas: int
    avisos: list[str] = []
    xml: str


class ConsigneeIn(BaseModel):
    destinatario: str = Field(min_length=1, max_length=128)
    consignee_code: str = Field(min_length=1, max_length=32)
    descripcion: Optional[str] = None
