import 'package:campus_ai_client/core/app_localizations.dart';
import 'package:campus_ai_client/data/source_models.dart';
import 'package:flutter/material.dart';

/// Renders the deliberately small JSON Schema subset supported by Client v1.
class DynamicConfigForm extends StatefulWidget {
  const DynamicConfigForm({
    required this.schema,
    required this.formKey,
    required this.onChanged,
    this.initialValues = const {},
    super.key,
  });

  final JsonMap schema;
  final GlobalKey<FormState> formKey;
  final ValueChanged<JsonMap> onChanged;
  final JsonMap initialValues;

  @override
  State<DynamicConfigForm> createState() => _DynamicConfigFormState();
}

class _DynamicConfigFormState extends State<DynamicConfigForm> {
  final Map<String, TextEditingController> _controllers = {};
  final JsonMap _values = {};
  late final Map<String, JsonMap> _properties;
  late final Set<String> _required;

  @override
  void initState() {
    super.initState();
    final rawProperties = widget.schema['properties'];
    _properties = rawProperties is Map
        ? rawProperties.map(
            (key, value) => MapEntry(key.toString(), _propertyMap(value)),
          )
        : const {};
    _required = ((widget.schema['required'] as List?) ?? const [])
        .map((value) => value.toString())
        .toSet();

    for (final entry in _properties.entries) {
      final name = entry.key;
      final property = entry.value;
      if (property['x-campus-secret'] == true) continue;
      final defaultValue = widget.initialValues.containsKey(name)
          ? widget.initialValues[name]
          : property['default'];
      if (defaultValue != null) _values[name] = defaultValue;
      final type = _primaryType(property['type']);
      if (type == 'boolean' &&
          defaultValue == null &&
          _required.contains(name)) {
        _values[name] = false;
      }
      if (type == 'string' || type == 'number' || type == 'integer') {
        _controllers[name] = TextEditingController(
          text: defaultValue?.toString() ?? '',
        );
      } else if (type == 'array') {
        final values = defaultValue is List ? defaultValue : const [];
        _controllers[name] = TextEditingController(text: values.join('\n'));
      }
    }
    WidgetsBinding.instance.addPostFrameCallback((_) => _notify());
  }

  @override
  void dispose() {
    for (final controller in _controllers.values) {
      controller.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Form(
      key: widget.formKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          for (final entry in _properties.entries) ...[
            _buildField(entry.key, entry.value),
            const SizedBox(height: 14),
          ],
        ],
      ),
    );
  }

  Widget _buildField(String name, JsonMap property) {
    final label = property['title'] as String? ?? _humanize(name);
    final description = property['description'] as String?;
    final required = _required.contains(name);

    if (property['x-campus-secret'] == true) {
      return Card(
        color: Theme.of(context).colorScheme.surfaceContainerHighest,
        child: ListTile(
          leading: const Icon(Icons.key_outlined),
          title: Text(label),
          subtitle: Text(context.strings.secretConfigHint),
        ),
      );
    }

    final rawEnum = property['enum'];
    if (rawEnum is List && rawEnum.isNotEmpty) {
      final values = rawEnum.map((value) => value.toString()).toList();
      return DropdownButtonFormField<String>(
        initialValue: _values[name]?.toString(),
        decoration: InputDecoration(
          labelText: _fieldLabel(label, required),
          helperText: description,
          border: const OutlineInputBorder(),
        ),
        items: [
          for (final value in values)
            DropdownMenuItem(value: value, child: Text(value)),
        ],
        validator: (value) => required && value == null
            ? context.strings.selectField(label)
            : null,
        onChanged: (value) {
          _setValue(name, value);
        },
      );
    }

    switch (_primaryType(property['type'])) {
      case 'string':
        return TextFormField(
          controller: _controllers[name],
          decoration: InputDecoration(
            labelText: _fieldLabel(label, required),
            helperText: description,
            border: const OutlineInputBorder(),
          ),
          keyboardType: property['format'] == 'uri'
              ? TextInputType.url
              : TextInputType.text,
          validator: (value) => _validateString(
            value,
            label: label,
            property: property,
            required: required,
          ),
          onChanged: (value) =>
              _setValue(name, value.trim().isEmpty ? null : value.trim()),
        );
      case 'number':
      case 'integer':
        final integer = _primaryType(property['type']) == 'integer';
        return TextFormField(
          controller: _controllers[name],
          decoration: InputDecoration(
            labelText: _fieldLabel(label, required),
            helperText: description,
            border: const OutlineInputBorder(),
          ),
          keyboardType: TextInputType.numberWithOptions(decimal: !integer),
          validator: (value) => _validateNumber(
            value,
            label: label,
            property: property,
            required: required,
            integer: integer,
          ),
          onChanged: (value) {
            final parsed = integer
                ? int.tryParse(value)
                : double.tryParse(value);
            _setValue(name, parsed);
          },
        );
      case 'boolean':
        return FormField<bool>(
          initialValue: _values[name] as bool? ?? false,
          builder: (field) => InputDecorator(
            decoration: InputDecoration(
              labelText: _fieldLabel(label, required),
              helperText: description,
              border: const OutlineInputBorder(),
            ),
            child: Row(
              children: [
                Expanded(child: Text((field.value ?? false).toString())),
                Switch(
                  value: field.value ?? false,
                  onChanged: (value) {
                    field.didChange(value);
                    _setValue(name, value);
                  },
                ),
              ],
            ),
          ),
        );
      case 'array':
        final items = property['items'];
        final itemType = items is Map ? _primaryType(items['type']) : null;
        if (itemType != 'string') {
          return _UnsupportedField(name: name, type: 'array<$itemType>');
        }
        return TextFormField(
          controller: _controllers[name],
          minLines: 2,
          maxLines: 5,
          decoration: InputDecoration(
            labelText: _fieldLabel(label, required),
            helperText: description ?? context.strings.listFieldHint,
            border: const OutlineInputBorder(),
          ),
          validator: (value) {
            final items = _stringItems(value ?? '');
            final minimum = property['minItems'] as int? ?? (required ? 1 : 0);
            return items.length < minimum
                ? context.strings.minItems(label, minimum)
                : null;
          },
          onChanged: (value) => _setValue(name, _stringItems(value)),
        );
      default:
        return _UnsupportedField(name: name, type: property['type'].toString());
    }
  }

  String? _validateString(
    String? value, {
    required String label,
    required JsonMap property,
    required bool required,
  }) {
    final normalized = value?.trim() ?? '';
    if (required && normalized.isEmpty) {
      return context.strings.requiredField(label);
    }
    final minimum = property['minLength'] as int? ?? 0;
    if (normalized.isNotEmpty && normalized.length < minimum) {
      return context.strings.minLength(label, minimum);
    }
    if (normalized.isNotEmpty && property['format'] == 'uri') {
      final uri = Uri.tryParse(normalized);
      if (uri == null ||
          !uri.hasAuthority ||
          (uri.scheme != 'http' && uri.scheme != 'https') ||
          uri.userInfo.isNotEmpty) {
        return context.strings.invalidUrl;
      }
    }
    return null;
  }

  String? _validateNumber(
    String? value, {
    required String label,
    required JsonMap property,
    required bool required,
    required bool integer,
  }) {
    final normalized = value?.trim() ?? '';
    if (normalized.isEmpty) {
      return required ? context.strings.requiredField(label) : null;
    }
    final number = integer
        ? int.tryParse(normalized)
        : double.tryParse(normalized);
    if (number == null) {
      return integer
          ? context.strings.enterInteger
          : context.strings.enterNumber;
    }
    final minimum = property['minimum'] as num?;
    final maximum = property['maximum'] as num?;
    if (minimum != null && number < minimum) {
      return context.strings.minimumValue(label, minimum);
    }
    if (maximum != null && number > maximum) {
      return context.strings.maximumValue(label, maximum);
    }
    return null;
  }

  void _setValue(String name, Object? value) {
    if (value == null || (value is List && value.isEmpty)) {
      _values.remove(name);
    } else {
      _values[name] = value;
    }
    _notify();
  }

  void _notify() => widget.onChanged(Map.unmodifiable(_values));

  static String? _primaryType(Object? value) {
    if (value is String) return value;
    if (value is List) {
      for (final item in value) {
        if (item != 'null') return item.toString();
      }
    }
    return null;
  }

  static JsonMap _propertyMap(Object? value) {
    if (value is! Map) return {'type': 'unsupported'};
    return value.map((key, itemValue) => MapEntry(key.toString(), itemValue));
  }

  static List<String> _stringItems(String value) => value
      .split(RegExp(r'[,\n]'))
      .map((item) => item.trim())
      .where((item) => item.isNotEmpty)
      .toSet()
      .toList(growable: false);

  static String _humanize(String value) => value
      .split('_')
      .where((part) => part.isNotEmpty)
      .map((part) => '${part[0].toUpperCase()}${part.substring(1)}')
      .join(' ');

  static String _fieldLabel(String label, bool required) =>
      required ? '$label *' : label;
}

class _UnsupportedField extends StatelessWidget {
  const _UnsupportedField({required this.name, required this.type});

  final String name;
  final String type;

  @override
  Widget build(BuildContext context) {
    return FormField<void>(
      validator: (_) => context.strings.unsupportedField(name, type),
      builder: (field) => Card(
        color: Theme.of(context).colorScheme.errorContainer,
        child: ListTile(
          leading: const Icon(Icons.error_outline),
          title: Text(context.strings.cannotConfigure(name)),
          subtitle: Text(context.strings.unsupportedSchemaType(type)),
        ),
      ),
    );
  }
}
