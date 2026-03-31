# Menstruation Tracker for Home Assistant

[English](#english) | [中文](#中文)

---

## English

A Home Assistant custom integration for tracking menstrual cycles with predictions and calendar support.

### Features

- 📅 Track menstrual periods with start and end dates
- 🔮 Predict next period based on historical data
- 📊 Calculate average cycle length and period duration
- 👥 Support multiple users via Person entity linking
- 🗓️ Calendar integration for viewing periods
- 🎨 Custom Lovelace card for easy tracking
- 🌍 Multi-language support (EN, ES, FR, JA, KO, RU, ZH-CN)

### Installation

#### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/wuxinyumrx/ha_menstruation`
6. Select category: "Integration"
7. Click "Add"
8. Find "Menstruation Tracker" in HACS and install it
9. Restart Home Assistant

#### Manual Installation

1. Download the latest release from GitHub
2. Copy the `custom_components/menstruation` folder to your `config/custom_components/` directory
3. Restart Home Assistant

### Configuration

1. Go to Settings → Devices & Services
2. Click "+ Add Integration"
3. Search for "Menstruation Tracker"
4. Follow the configuration flow
5. (Optional) Link to a Person entity for multi-user support

### Usage

#### Recording a Period

Use the `menstruation.apply_day` service to record menstrual days:

```yaml
service: menstruation.apply_day
data:
  date: "2024-03-15"
  person: person.your_name  # Optional, for multi-user setups
```

#### Entities Created

- **Sensor**: Current phase (period/ovulation/safe)
- **Binary Sensor**: Is currently in period
- **Calendar**: View all periods and predictions

#### Custom Lovelace Card

Add the custom card to your dashboard:

```yaml
type: custom:menstruation-card
entity: sensor.menstruation
```

### Attributes

The sensor provides these attributes:

- `predicted_start`: Next predicted period start date
- `predicted_end`: Next predicted period end date
- `cycle_length`: Average cycle length in days
- `period_length`: Average period duration in days
- `last_start`: Last period start date
- `last_end`: Last period end date

### Support

- 🐛 [Report Issues](https://github.com/wuxinyumrx/ha_menstruation/issues)
- 💬 [Discussions](https://github.com/wuxinyumrx/ha_menstruation/discussions)

### License

MIT License - see [LICENSE](LICENSE) file for details

---

## 中文

Home Assistant 月经周期追踪自定义集成，支持周期预测和日历功能。

### 功能特性

- 📅 追踪月经周期的开始和结束日期
- 🔮 基于历史数据预测下次月经
- 📊 计算平均周期长度和经期时长
- 👥 支持通过 Person 实体关联多用户
- 🗓️ 日历集成，可视化查看周期
- 🎨 自定义 Lovelace 卡片，方便记录
- 🌍 多语言支持（英语、西班牙语、法语、日语、韩语、俄语、简体中文）

### 安装方法

#### HACS 安装（推荐）

1. 在 Home Assistant 中打开 HACS
2. 点击"集成"
3. 点击右上角的三个点
4. 选择"自定义存储库"
5. 添加此仓库地址：`https://github.com/wuxinyumrx/ha_menstruation`
6. 选择类别："Integration"
7. 点击"添加"
8. 在 HACS 中找到"Menstruation Tracker"并安装
9. 重启 Home Assistant

#### 手动安装

1. 从 GitHub 下载最新版本
2. 将 `custom_components/menstruation` 文件夹复制到你的 `config/custom_components/` 目录
3. 重启 Home Assistant

### 配置

1. 进入 设置 → 设备与服务
2. 点击"+ 添加集成"
3. 搜索"Menstruation Tracker"
4. 按照配置流程操作
5. （可选）关联到 Person 实体以支持多用户

### 使用方法

#### 记录月经日期

使用 `menstruation.apply_day` 服务记录月经日期：

```yaml
service: menstruation.apply_day
data:
  date: "2024-03-15"
  person: person.your_name  # 可选，多用户时使用
```

#### 创建的实体

- **传感器**：当前阶段（经期/排卵期/安全期）
- **二进制传感器**：是否处于经期
- **日历**：查看所有周期和预测

#### 自定义 Lovelace 卡片

将自定义卡片添加到仪表板：

```yaml
type: custom:menstruation-card
entity: sensor.menstruation
```

### 属性说明

传感器提供以下属性：

- `predicted_start`：预测的下次月经开始日期
- `predicted_end`：预测的下次月经结束日期
- `cycle_length`：平均周期长度（天）
- `period_length`：平均经期时长（天）
- `last_start`：上次月经开始日期
- `last_end`：上次月经结束日期

### 支持

- 🐛 [报告问题](https://github.com/wuxinyumrx/ha_menstruation/issues)
- 💬 [讨论区](https://github.com/wuxinyumrx/ha_menstruation/discussions)

### 许可证

MIT 许可证 - 详见 [LICENSE](LICENSE) 文件
