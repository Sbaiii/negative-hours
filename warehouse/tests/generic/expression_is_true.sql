{#- Fails for every row where `expression` is not true. -#}
{% test expression_is_true(model, expression) %}

select *
from {{ model }}
where not ({{ expression }})

{% endtest %}
