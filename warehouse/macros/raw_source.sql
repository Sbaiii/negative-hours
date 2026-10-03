{#-
  Raw Parquet files are read through an ABSOLUTE path, so the staging views work
  no matter which directory they are later queried from (repo root, analysis/, ...).

  The path is <repo>/data/raw, where <repo> is the parent of the dbt project
  directory (warehouse/). Override it with `--vars '{raw_data_dir: /some/path}'`
  or the environment variable NEGATIVE_HOURS_RAW_DIR.
-#}

{% macro raw_data_dir() %}
    {%- set project_dir = invocation_args_dict.get('project_dir') or '.' -%}
    {%- if not project_dir.startswith('/') -%}
        {%- set project_dir = env_var('PWD') ~ '/' ~ project_dir -%}
    {%- endif -%}
    {%- set default = env_var('NEGATIVE_HOURS_RAW_DIR', normalize_path(project_dir ~ '/../data/raw')) -%}
    {{- return(var('raw_data_dir', default)) -}}
{% endmacro %}


{% macro normalize_path(path) %}
    {#- Resolve "." and ".." segments: /a/warehouse/../data -> /a/data -#}
    {%- set parts = [] -%}
    {%- for part in path.split('/') -%}
        {%- if part == '..' and parts -%}
            {%- do parts.pop() -%}
        {%- elif part not in ('', '.', '..') -%}
            {%- do parts.append(part) -%}
        {%- endif -%}
    {%- endfor -%}
    {{- return('/' ~ parts | join('/')) -}}
{% endmacro %}


{% macro raw_source(table_name) %}
    {#- Calling source() keeps the raw tables in the lineage graph and docs. -#}
    {%- do source('raw', table_name) -%}
    read_parquet('{{ raw_data_dir() }}/{{ table_name }}/**/*.parquet', hive_partitioning = true)
{%- endmacro %}
