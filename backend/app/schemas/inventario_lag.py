from typing import Literal, Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Inventario
# ---------------------------------------------------------------------------


class PieceInInventory(BaseModel):
    barcode: str
    rack: str


class RackSummary(BaseModel):
    rack: str
    piezas: int


class InventoryResponse(BaseModel):
    total_piezas: int
    total_racks: int
    piezas: list[PieceInInventory]
    resumen_racks: list[RackSummary]


class PiezaDetalle(BaseModel):
    """Una pieza con las columnas equivalentes al reporte ResumenCodigosDeBarra del WMS.

    Combina Barcode Information V2 (detalle) con Pieces in Inventory (ubicacion).
    """

    status: str = ""
    barcode: str = ""
    shipment_nr: str = ""
    house: str = ""
    exporter: str = ""
    consignee: str = ""
    carrier: str = ""
    location: Optional[str] = None
    product: str = ""
    description: str = ""
    tipo: str = ""
    largo_cm: Optional[float] = None
    ancho_cm: Optional[float] = None
    alto_cm: Optional[float] = None
    largo_inch: Optional[float] = None
    ancho_inch: Optional[float] = None
    alto_inch: Optional[float] = None
    unidades: Optional[int] = None
    precio: Optional[float] = None
    peso: Optional[float] = None
    valor_caja: Optional[float] = None


class InventarioCompleto(BaseModel):
    total_piezas: int
    total_recibidas: int
    total_pendientes: int
    total_unidades: int
    valor_total: float
    guias_consultadas: list[str]
    avisos: list[str]
    piezas: list[PiezaDetalle]


# ---------------------------------------------------------------------------
# Ordenes de compra
# ---------------------------------------------------------------------------


class PurchaseOrderItem(BaseModel):
    farm_code: str = Field(max_length=32, description="Codigo del proveedor/finca")
    length: float
    width: float
    height: float
    gross_weight: float
    unit_of_measurement: Literal["CM", "INCH"] = "CM"
    barcode: Optional[str] = Field(default=None, max_length=11)
    box_size: Optional[str] = Field(default=None, max_length=16)
    product_code: Optional[str] = Field(default=None, max_length=32)
    product_description: Optional[str] = Field(default=None, max_length=128)
    packing: Optional[int] = None
    unit_price: Optional[float] = None
    ship_to_code: Optional[str] = Field(default=None, max_length=32)
    carrier_code: Optional[str] = Field(default=None, max_length=8)
    dispatch_date: Optional[str] = Field(default=None, description="Formato YYYY-MM-DD")
    comments: Optional[str] = Field(default=None, max_length=256)


class PurchaseOrderIn(BaseModel):
    consignee_code: str = Field(max_length=32)
    destination_port_code: str = Field(max_length=3, description="Codigo IATA")
    post_type: Literal["LOCAL", "FINAL"]
    warehouse_code: Optional[str] = Field(default=None, max_length=8, description="Requerido si post_type=LOCAL")
    po_number: Optional[str] = Field(default=None, max_length=32)
    origin_port_code: Optional[str] = Field(default=None, max_length=3)
    estimated_date: Optional[str] = Field(default=None, description="Formato YYYY-MM-DD")
    comments: Optional[str] = Field(default=None, max_length=256)
    accion: Literal["INSERT", "DELETE"] = "INSERT"
    items: list[PurchaseOrderItem] = Field(min_length=1)


class PurchaseOrderResult(BaseModel):
    is_success: bool
    errors: list[dict[str, str]] = []
    raw_response: str


# ---------------------------------------------------------------------------
# Ordenes de venta
# ---------------------------------------------------------------------------


class SalesOrderBox(BaseModel):
    boxId: str = Field(max_length=16)
    unitPrice: Optional[float] = None
    markCode: Optional[str] = Field(default=None, max_length=16)
    units: Optional[int] = None


class SalesOrderIn(BaseModel):
    customerId: str = Field(max_length=16)
    carrierId: str = Field(max_length=16)
    shipDate: str = Field(description="Formato MM/dd/yyyy")
    orderNumber: str = Field(max_length=16)
    idOrder: int
    poNumber: Optional[str] = Field(default=None, max_length=16)
    generateBOL: Optional[bool] = None
    boxIds: list[SalesOrderBox] = Field(min_length=1)


class SalesOrderCancelIn(BaseModel):
    idOrder: int
