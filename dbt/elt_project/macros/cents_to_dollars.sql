-- Örnek macro: kuruşu liraya çevir
-- Kullanım: {{ cents_to_dollars('amount_cents') }}

{% macro cents_to_dollars(column_name, precision=2) %}
    ({{ column_name }} / 100.0)::NUMERIC(12, {{ precision }})
{% endmacro %}
