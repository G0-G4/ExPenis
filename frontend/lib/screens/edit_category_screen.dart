import 'package:flutter/material.dart';

import 'package:expenis_mobile/models/category.dart';
import 'package:expenis_mobile/service/category_service.dart';
import 'package:expenis_mobile/theme.dart';
import 'package:expenis_mobile/widgets/app_loading_spinner.dart';
import 'package:expenis_mobile/widgets/delete_dialog.dart';

class EditCategoryScreen extends StatefulWidget {
  final int categoryId;

  const EditCategoryScreen({super.key, required this.categoryId});

  @override
  State<EditCategoryScreen> createState() => _EditCategoryScreenState();
}

class _EditCategoryScreenState extends State<EditCategoryScreen> {
  final CategoryService _categoryService = CategoryService();
  final _formKey = GlobalKey<FormState>();
  TextEditingController? _nameController;
  CategoryType? _type;
  bool _isSaving = false;

  @override
  void initState() {
    super.initState();
    _fetchCategory();
  }

  Future<void> _fetchCategory() async {
    try {
      final category = await _categoryService.fetchCategory(widget.categoryId);
      if (!mounted) return;
      setState(() {
        _nameController = TextEditingController(text: category.name);
        _type = category.type;
      });
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Failed to load category: $e')));
    }
  }

  Future<void> _updateCategory() async {
    if (_nameController == null || _type == null) return;
    if (!_formKey.currentState!.validate()) return;
    setState(() => _isSaving = true);
    try {
      await _categoryService.updateCategory(
        Category(
          id: widget.categoryId,
          name: _nameController!.text.trim(),
          type: _type!,
        ),
      );
      if (!mounted) return;
      Navigator.pop(context, true);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Failed to update category: $e')));
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  Future<void> _deleteCategory() async {
    final confirmed = await showDeleteDialog(
      context: context,
      resourceName: 'category',
    );
    if (!confirmed || !mounted) return;
    try {
      await _categoryService.deleteCategory(widget.categoryId);
      if (!mounted) return;
      Navigator.pop(context, true);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Failed to delete category: $e')));
    }
  }

  @override
  void dispose() {
    _nameController?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Edit Category'),
        actions: [
          if (_nameController != null)
            IconButton(
              icon: Icon(
                Icons.delete_outline,
                color: Theme.of(context).colorScheme.error,
              ),
              tooltip: 'Delete',
              onPressed: _deleteCategory,
            ),
        ],
      ),
      body: _nameController == null || _type == null
          ? const Center(child: CircularProgressIndicator())
          : Form(
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
                    selected: {_type!},
                    onSelectionChanged: (selection) =>
                        setState(() => _type = selection.first),
                  ),
                  const SizedBox(height: AppTheme.space32),
                  FilledButton(
                    onPressed: _isSaving ? null : _updateCategory,
                    child: _isSaving
                        ? const AppLoadingSpinner()
                        : const Text('Save Changes'),
                  ),
                ],
              ),
            ),
    );
  }
}
