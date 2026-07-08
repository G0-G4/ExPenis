import 'package:flutter/material.dart';

import 'package:expenis_mobile/models/category.dart';
import 'package:expenis_mobile/service/category_service.dart';
import 'package:expenis_mobile/theme.dart';
import 'package:expenis_mobile/widgets/app_loading_spinner.dart';

class CreateCategoryScreen extends StatefulWidget {
  const CreateCategoryScreen({super.key});

  @override
  State<CreateCategoryScreen> createState() => _CreateCategoryScreenState();
}

class _CreateCategoryScreenState extends State<CreateCategoryScreen> {
  final CategoryService _categoryService = CategoryService();
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  CategoryType _type = CategoryType.expense;
  bool _isSaving = false;

  Future<void> _createCategory() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _isSaving = true);
    try {
      final newCategory = await _categoryService.createCategory(
        _nameController.text.trim(),
        _type,
      );
      if (!mounted) return;
      Navigator.pop(context, newCategory);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Failed to create category: $e')));
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  @override
  void dispose() {
    _nameController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('New Category')),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: AppTheme.screenPadding,
          children: [
            TextFormField(
              controller: _nameController,
              decoration: const InputDecoration(
                labelText: 'Category Name',
                prefixIcon: Icon(Icons.folder_outlined),
              ),
              textCapitalization: TextCapitalization.words,
              validator: (value) => (value == null || value.isEmpty)
                  ? 'Please enter a name'
                  : null,
            ),
            const SizedBox(height: AppTheme.space24),
            Text(
              'Type',
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: AppTheme.space8),
            SegmentedButton<CategoryType>(
              segments: const [
                ButtonSegment(
                  value: CategoryType.income,
                  label: Text('Income'),
                  icon: Icon(Icons.arrow_downward_rounded, size: 16),
                ),
                ButtonSegment(
                  value: CategoryType.expense,
                  label: Text('Expense'),
                  icon: Icon(Icons.arrow_upward_rounded, size: 16),
                ),
              ],
              selected: {_type},
              onSelectionChanged: (selection) =>
                  setState(() => _type = selection.first),
            ),
            const SizedBox(height: AppTheme.space32),
            FilledButton(
              onPressed: _isSaving ? null : _createCategory,
              child: _isSaving
                  ? const AppLoadingSpinner()
                  : const Text('Create Category'),
            ),
          ],
        ),
      ),
    );
  }
}
