# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Declarative shape of the demo dataset.

This module holds data, not logic. `generator.py` reads it and writes DuckDB.
Every column names one strategy. Every `Ref` and `ParentKey` declares a foreign
key, and the generator refuses to write a file where one of them joins nothing.
"""

from dataclasses import dataclass

# --- strategies -------------------------------------------------------------


@dataclass(frozen=True)
class Key:
    """A unique id per row: a prefix plus a zero padded counter."""

    prefix: str
    width: int = 5


@dataclass(frozen=True)
class Ref:
    """A foreign key. Values come from a column of an earlier table."""

    table: str
    column: str


@dataclass(frozen=True)
class ParentKey:
    """A foreign key to the parent table that owns this row."""


@dataclass(frozen=True)
class Sequence:
    """A counter that restarts for every parent row."""

    start: int = 1


@dataclass(frozen=True)
class Pick:
    """One value out of a fixed set. `weights` skews the draw."""

    values: tuple
    weights: tuple[int, ...] | None = None


@dataclass(frozen=True)
class MapFrom:
    """A value looked up from another column of the same row."""

    column: str
    mapping: dict


@dataclass(frozen=True)
class Copy:
    """A value copied from the row that a foreign key column points to."""

    via: str
    column: str


@dataclass(frozen=True)
class Int:
    """A whole number between two bounds."""

    low: int
    high: int


@dataclass(frozen=True)
class Num:
    """A decimal number between two bounds."""

    low: float
    high: float
    decimals: int = 2


@dataclass(frozen=True)
class When:
    """A timestamp between two dates, written as YYYY-MM-DD."""

    start: str
    end: str


@dataclass(frozen=True)
class After:
    """A timestamp placed some hours after another column.

    `via` reads the base column from the row a foreign key points to.
    `only_when` names a column and the values that make this column non null.
    """

    column: str
    min_hours: int
    max_hours: int
    via: str | None = None
    only_when: tuple[str, tuple] | None = None


# --- structure --------------------------------------------------------------


@dataclass(frozen=True)
class Column:
    name: str
    type: str
    value: object


@dataclass(frozen=True)
class Parent:
    """Ties a table's rows to the rows of an owning table."""

    table: str
    column: str
    per_row: tuple[int, int]


@dataclass(frozen=True)
class Table:
    name: str
    columns: tuple[Column, ...]
    rows: int | None = None
    parent: Parent | None = None


@dataclass(frozen=True)
class Spec:
    tables: tuple[Table, ...]
    seed: int = 4242


# --- category sets ----------------------------------------------------------

CITY_STATE = {
    "sao paulo": "SP",
    "campinas": "SP",
    "rio de janeiro": "RJ",
    "belo horizonte": "MG",
    "brasilia": "DF",
    "curitiba": "PR",
    "porto alegre": "RS",
    "salvador": "BA",
    "fortaleza": "CE",
    "recife": "PE",
    "manaus": "AM",
    "goiania": "GO",
}

PRODUCT_CATEGORIES = (
    "cama_mesa_banho",
    "beleza_saude",
    "esporte_lazer",
    "informatica_acessorios",
    "moveis_decoracao",
    "utilidades_domesticas",
    "relogios_presentes",
    "telefonia",
    "ferramentas_jardim",
    "automotivo",
    "brinquedos",
    "papelaria",
)

PRODUCT_CATEGORY_WEIGHTS = (170, 150, 120, 110, 95, 85, 70, 60, 50, 40, 30, 20)

# The seeded sample workbook charts orders that are not delivered. Real order
# books deliver about 97%, which would leave those charts with a handful of
# rows per month, so this skew keeps a readable 12% undelivered.
ORDER_STATUSES = ("delivered", "shipped", "canceled", "invoiced", "processing", "unavailable")
ORDER_STATUS_WEIGHTS = (880, 45, 25, 20, 18, 12)

PAYMENT_TYPES = ("credit_card", "boleto", "voucher", "debit_card")
PAYMENT_TYPE_WEIGHTS = (740, 190, 55, 15)

REVIEW_TITLES = (None, None, None, "recomendo", "muito bom", "nao recomendo", "chegou atrasado")
REVIEW_MESSAGES = (
    None,
    None,
    "Produto entregue antes do prazo.",
    "Chegou tudo certo, embalagem perfeita.",
    "O produto veio com defeito.",
    "Ainda nao recebi o pedido.",
    "Atendimento rapido e eficiente.",
)


# --- the dataset ------------------------------------------------------------

DEMO_SPEC = Spec(
    tables=(
        Table(
            name="geolocation",
            rows=150,
            columns=(
                Column("geolocation_zip_code_prefix", "VARCHAR", Key(prefix="0", width=4)),
                Column("geolocation_lat", "DOUBLE", Num(-30.0, 0.5, 6)),
                Column("geolocation_lng", "DOUBLE", Num(-70.0, -35.0, 6)),
                Column("geolocation_city", "VARCHAR", Pick(tuple(CITY_STATE))),
                Column("geolocation_state", "VARCHAR", MapFrom("geolocation_city", CITY_STATE)),
            ),
        ),
        Table(
            name="customers",
            rows=400,
            columns=(
                Column("customer_id", "VARCHAR", Key("CUST-", 5)),
                Column("customer_unique_id", "VARCHAR", Key("CUNQ-", 5)),
                Column(
                    "customer_zip_code_prefix",
                    "VARCHAR",
                    Ref("geolocation", "geolocation_zip_code_prefix"),
                ),
                Column("customer_city", "VARCHAR", Copy("customer_zip_code_prefix", "geolocation_city")),
                Column("customer_state", "VARCHAR", Copy("customer_zip_code_prefix", "geolocation_state")),
            ),
        ),
        Table(
            name="sellers",
            rows=60,
            columns=(
                Column("seller_id", "VARCHAR", Key("SELL-", 4)),
                Column(
                    "seller_zip_code_prefix",
                    "VARCHAR",
                    Ref("geolocation", "geolocation_zip_code_prefix"),
                ),
                Column("seller_city", "VARCHAR", Copy("seller_zip_code_prefix", "geolocation_city")),
                Column("seller_state", "VARCHAR", Copy("seller_zip_code_prefix", "geolocation_state")),
            ),
        ),
        Table(
            name="products",
            rows=120,
            columns=(
                Column("product_id", "VARCHAR", Key("PROD-", 4)),
                Column(
                    "product_category_name",
                    "VARCHAR",
                    Pick(PRODUCT_CATEGORIES, PRODUCT_CATEGORY_WEIGHTS),
                ),
                Column("product_weight_g", "BIGINT", Int(50, 30000)),
                Column("product_length_cm", "BIGINT", Int(6, 100)),
                Column("product_height_cm", "BIGINT", Int(2, 80)),
                Column("product_width_cm", "BIGINT", Int(6, 100)),
            ),
        ),
        Table(
            name="orders",
            rows=2000,
            columns=(
                Column("order_id", "VARCHAR", Key("ORD-", 5)),
                Column("customer_id", "VARCHAR", Ref("customers", "customer_id")),
                Column("order_status", "VARCHAR", Pick(ORDER_STATUSES, ORDER_STATUS_WEIGHTS)),
                Column("order_purchase_timestamp", "TIMESTAMP", When("2016-09-01", "2018-10-31")),
                Column("order_approved_at", "TIMESTAMP", After("order_purchase_timestamp", 1, 48)),
                Column(
                    "order_delivered_carrier_date",
                    "TIMESTAMP",
                    After(
                        "order_approved_at",
                        12,
                        240,
                        only_when=("order_status", ("delivered", "shipped")),
                    ),
                ),
                Column(
                    "order_delivered_customer_date",
                    "TIMESTAMP",
                    After(
                        "order_delivered_carrier_date",
                        24,
                        480,
                        only_when=("order_status", ("delivered",)),
                    ),
                ),
                Column(
                    "order_estimated_delivery_date",
                    "TIMESTAMP",
                    After("order_purchase_timestamp", 168, 720),
                ),
            ),
        ),
        Table(
            name="orderitems",
            parent=Parent("orders", "order_id", per_row=(1, 4)),
            columns=(
                Column("order_id", "VARCHAR", ParentKey()),
                Column("order_item_id", "BIGINT", Sequence()),
                Column("product_id", "VARCHAR", Ref("products", "product_id")),
                Column("seller_id", "VARCHAR", Ref("sellers", "seller_id")),
                Column(
                    "shipping_limit_date",
                    "TIMESTAMP",
                    After("order_purchase_timestamp", 48, 336, via="order_id"),
                ),
                Column("price", "DOUBLE", Num(9.9, 899.0, 2)),
                Column("freight_value", "DOUBLE", Num(5.0, 60.0, 2)),
            ),
        ),
        Table(
            name="orderpayments",
            parent=Parent("orders", "order_id", per_row=(1, 2)),
            columns=(
                Column("order_id", "VARCHAR", ParentKey()),
                Column("payment_sequential", "BIGINT", Sequence()),
                Column("payment_type", "VARCHAR", Pick(PAYMENT_TYPES, PAYMENT_TYPE_WEIGHTS)),
                Column("payment_installments", "BIGINT", Int(1, 12)),
                Column("payment_value", "DOUBLE", Num(15.0, 1800.0, 2)),
            ),
        ),
        Table(
            name="orderreviews",
            parent=Parent("orders", "order_id", per_row=(1, 1)),
            columns=(
                Column("review_id", "VARCHAR", Key("REV-", 5)),
                Column("order_id", "VARCHAR", ParentKey()),
                Column("review_score", "BIGINT", Pick((1, 2, 3, 4, 5), (90, 50, 90, 220, 550))),
                Column("review_comment_title", "VARCHAR", Pick(REVIEW_TITLES)),
                Column("review_comment_message", "VARCHAR", Pick(REVIEW_MESSAGES)),
                Column(
                    "review_creation_date",
                    "TIMESTAMP",
                    After("order_purchase_timestamp", 48, 720, via="order_id"),
                ),
                Column("review_answer_timestamp", "TIMESTAMP", After("review_creation_date", 1, 96)),
            ),
        ),
    )
)
