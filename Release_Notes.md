---
pagetitle: Release Notes for stdatalog_dtk 
lang: en
header-includes: <link rel="icon" type="image/x-icon" href="_htmresc/favicon.png" />
---

::: {.row}
::: {.col-sm-12 .col-lg-4}

<center> 
# Release Notes for <mark>stdatalog_dtk</mark> 
Copyright &copy; 2025 STMicroelectronics
    
[![ST logo](../_htmresc/st_logo_2020.png)](https://www.st.com){.logo}
</center>


# Purpose

The **[stdatalog_dtk](https://github.com/STMicroelectronics/stdatalog_dtk)** (**dtk** acronym stands for **D**ata **T**ool**K**it) provides functionalities to realize a data processing pipeline that can handle data from various sources and process them in many different and customizable ways.
A data processing pipeline is a series of data processing elements connected in series, where the output of one element is the input of the next. These processing elements are called Plugins. The package provides an abstract Plugin class that must be inherited to create a new plugin that can be added to the pipeline.

Typycal uses of plugins are the following:
- Process, filter or transform data from sensors
- Send data to external services
- Store data in local files or databases
- Visualize data in a GUI application (PySide6-based)

Plugins can be chained together to create complex data processing pipelines combining then different use cases and functionalities.

It is designed to simplify the development of applications using data from ST sensors, providing complete hardware abstraction, making it easier to handle real-time data from connected ST system solutions or stored datasets.

The package is part of the **[STDATALOG-PYSDK](https://github.com/STMicroelectronics/stdatalog-pysdk)**, which is a set of libraries and tools that enable the development of applications for data logging and data monitoring.

:::

::: {.col-sm-12 .col-lg-8}
# Update History

::: {.collapse}
<input type="checkbox" id="collapse-section3" checked aria-hidden="true">
<label for="collapse-section3" aria-hidden="true">v1.2.0 / 20-Jun-25</label>
<div>


## Main Changes

### Maintenance Release

- Added support to Python 3.13

</div>
:::

::: {.collapse}
<input type="checkbox" id="collapse-section2" aria-hidden="true">
<label for="collapse-section2" aria-hidden="true">v1.1.0 / 9-Apr-25</label>
<div>


## Main Changes

### Maintenance Release

- **Added macos support.**
- Use the latest PySide6 version compatible w.r.t. architecture (Windows, Linux, macOS; 32bit, 64bit)

</div>
:::

::: {.collapse}
<input type="checkbox" id="collapse-section1"  aria-hidden="true">
<label for="collapse-section1" aria-hidden="true">v1.0.0 / 17-Jan-25</label>
<div>


## Main Changes

### First official release


</div>
:::

:::
:::

<footer class="sticky">
::: {.columns}
::: {.column width="95%"}
For complete documentation,
visit: [www.st.com](https://github.com/STMicroelectronics/stdatalog-pysdk)
:::
::: {.column width="5%"}
<abbr title="Based on template cx566953 version 2.0">Info</abbr>
:::
:::
</footer>
