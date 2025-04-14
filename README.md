# stdatalog_dtk

![latest tag](https://img.shields.io/github/v/tag/STMicroelectronics/stdatalog_dtk.svg?color=brightgreen)

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

## Features

- Manage a data pipeline
- Create and manage plugins
- Support for plugins to process data
- Integration with Qt for GUI applications

## Installation

To install the `stdatalog_dtk` package after downloading it, execute the following command from the package's root directory:
NOTE: Be sure to satisfy the requirements before installing the package ([see Requirements](#requirements)).

On Windows:
```sh
python -m pip install dist\stdatalog_dtk-1.1.0-py3-none-any.whl
```

On Linux/macOS:
```sh
python3 -m pip install dist/stdatalog_dtk-1.1.0-py3-none-any.whl
```

The package could also be installed as part of the **[STDATALOG-PYSDK](https://github.com/STMicroelectronics/stdatalog-pysdk)** by launching the SDK installation script from the SDK root folder:

On Windows:
```sh
.\STDATALOG-PYSDK_install.bat
```

On Linux/macOS:
```sh
./STDATALOG-PYSDK_install.sh
```

Source code is also available within the inner `stdatalog_dtk` folder.

## Requirements
The package requires the following dependencies:

- **[stdatalog_core](https://github.com/STMicroelectronics/stdatalog_core)**
- PySide6
	- 6.9.0 on Windows, Linux not aarch64 machines and macOS arm64 machines
	- 6.8.0.2 on Linux aarch64 machines
	- 6.7.3 on macOS x86_64 machines

## Usage
Please refer to the guide found **[here](https://htmlpreview.github.io/?https://raw.githubusercontent.com/STMicroelectronics/stdatalog_examples/refs/heads/main/dtk_plugins/documentation/doc.html)** for a complete and detailed explanation regarding the `stdatalog_dtk` package and the creation and execution of Plugins.
within the guide you will notice that we provide a set of tutorials with different complexity levels to help you get started with the package and Plugins development.

## License
This project is licensed under the BSD 3-Clause License - see the LICENSE.md file for details.