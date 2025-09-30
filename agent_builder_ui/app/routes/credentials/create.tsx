import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router';
import type { Route } from './+types/create';
import { Layout } from '../../components/layout/Layout';
import { Card, CardContent } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Badge } from '../../components/ui/Badge';
import { LoadingState } from '../../components/ui/Loading';
import { useCredentialCategories, useCredentialTypes, useCredentialTypeFields, useFormSubmit } from '../../hooks/useAPI';
import { api } from '../../lib/api';
import type { CredentialType, CredentialField, CredentialCreate } from '../../lib/types';

export function meta({}: Route.MetaArgs) {
  return [
    { title: "Add Credential - Agent Builder" },
    { name: "description", content: "Add a new service credential" },
  ];
}

interface FormData {
  name: string;
  description: string;
  credential_type: number;
  credential_details: Record<string, string>;
}

export default function CreateCredential() {
  const navigate = useNavigate();
  const { data: categories, loading: categoriesLoading } = useCredentialCategories();
  const [selectedCategoryId, setSelectedCategoryId] = useState<number | null>(null);
  const [selectedTypeId, setSelectedTypeId] = useState<number | null>(null);

  const { data: types, loading: typesLoading } = useCredentialTypes(selectedCategoryId || undefined);
  const { data: fields, loading: fieldsLoading } = useCredentialTypeFields(selectedTypeId);

  const [formData, setFormData] = useState<FormData>({
    name: '',
    description: '',
    credential_type: 0,
    credential_details: {}
  });

  const { submit, loading: submitting, error } = useFormSubmit((data: CredentialCreate) => api.createCredential(data));

  // Reset fields when type changes
  useEffect(() => {
    if (selectedTypeId) {
      setFormData(prev => ({
        ...prev,
        credential_type: selectedTypeId,
        credential_details: {}
      }));
    }
  }, [selectedTypeId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.name.trim()) {
      alert('Please enter a name for the credential');
      return;
    }

    if (!formData.credential_type || formData.credential_type <= 0) {
      alert('Please select a credential type');
      return;
    }

    // Validate required fields
    if (fields) {
      const requiredFields = fields.filter(field => field.is_required);
      const missingFields = requiredFields.filter(field =>
        !formData.credential_details[field.field_name]?.trim()
      );

      if (missingFields.length > 0) {
        alert(`Please fill in all required fields: ${missingFields.map(f => f.field_name).join(', ')}`);
        return;
      }
    }

    try {
      await submit(formData);
      navigate('/credentials');
    } catch (err) {
      // Error is handled by the hook
    }
  };

  const handleFieldChange = (fieldName: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      credential_details: {
        ...prev.credential_details,
        [fieldName]: value
      }
    }));
  };

  const renderField = (field: CredentialField) => {
    const value = formData.credential_details[field.field_name] || '';

    const baseProps = {
      id: field.field_name,
      value,
      onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
        handleFieldChange(field.field_name, e.target.value),
      placeholder: field.placeholder || `Enter ${field.field_name}`,
      required: field.is_required,
      className: "w-full"
    };

    switch (field.field_type) {
      case 'password':
        return (
          <Input
            {...baseProps}
            type="password"
            autoComplete="new-password"
          />
        );
      case 'email':
        return (
          <Input
            {...baseProps}
            type="email"
          />
        );
      case 'url':
        return (
          <Input
            {...baseProps}
            type="url"
          />
        );
      case 'number':
        return (
          <Input
            {...baseProps}
            type="number"
          />
        );
      case 'textarea':
        return (
          <textarea
            {...baseProps}
            rows={3}
            className="w-full rounded-md border border-[#233648] bg-[#1a2633] px-3 py-2 text-sm text-white placeholder:text-gray-400 focus:border-[#1173d4] focus:outline-none focus:ring-1 focus:ring-[#1173d4]"
          />
        );
      case 'checkbox':
        return (
          <input
            type="checkbox"
            id={field.field_name}
            checked={value === 'true'}
            onChange={(e) => handleFieldChange(field.field_name, e.target.checked ? 'true' : 'false')}
            className="rounded border border-[#233648] bg-[#1a2633] text-[#1173d4] focus:ring-[#1173d4]"
          />
        );
      default:
        return (
          <Input
            {...baseProps}
            type="text"
          />
        );
    }
  };

  return (
    <Layout>
      <div className="mx-auto max-w-4xl">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-2 text-sm text-gray-400 mb-2">
            <Link to="/credentials" className="hover:text-white">Credentials</Link>
            <span>/</span>
            <span>Add Credential</span>
          </div>
          <h1 className="text-white text-3xl font-bold leading-tight tracking-tight">
            Add Credential
          </h1>
          <p className="text-gray-400 mt-1">
            Connect to external services by adding your credentials.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Basic Information */}
          <Card>
            <CardContent className="pt-6">
              <h2 className="text-xl font-semibold text-white mb-4">Basic Information</h2>

              <div className="space-y-4">
                <div>
                  <label htmlFor="name" className="block text-sm font-medium text-gray-300 mb-2">
                    Name *
                  </label>
                  <Input
                    id="name"
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="e.g., My OpenAI API"
                    required
                  />
                </div>

                <div>
                  <label htmlFor="description" className="block text-sm font-medium text-gray-300 mb-2">
                    Description
                  </label>
                  <textarea
                    id="description"
                    value={formData.description}
                    onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                    placeholder="Optional description for this credential"
                    rows={3}
                    className="w-full rounded-md border border-[#233648] bg-[#1a2633] px-3 py-2 text-sm text-white placeholder:text-gray-400 focus:border-[#1173d4] focus:outline-none focus:ring-1 focus:ring-[#1173d4]"
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Service Selection */}
          <Card>
            <CardContent className="pt-6">
              <h2 className="text-xl font-semibold text-white mb-4">Service Type</h2>

              {categoriesLoading ? (
                <LoadingState>Loading service categories...</LoadingState>
              ) : (
                <div className="space-y-6">
                  {/* Category Selection */}
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-3">
                      Select Category *
                    </label>
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                      {categories?.results?.map((category) => (
                        <button
                          key={category.id}
                          type="button"
                          onClick={() => {
                            setSelectedCategoryId(category.id);
                            setSelectedTypeId(null);
                          }}
                          className={`p-4 rounded-lg border text-left transition-all ${
                            selectedCategoryId === category.id
                              ? 'border-[#1173d4] bg-[#1173d4]/10 text-white'
                              : 'border-[#233648] bg-[#1a2633] text-gray-300 hover:border-[#1173d4]/50'
                          }`}
                        >
                          <div className="flex items-center gap-2 mb-2">
                            {category.icon && (
                              <span className="material-symbols-outlined text-base">
                                {category.icon}
                              </span>
                            )}
                            <span className="font-medium">{category.name}</span>
                          </div>
                          <p className="text-xs text-gray-400">{category.description}</p>
                          <Badge size="sm" status="info" className="mt-2">
                            {category.types_count || 0} types
                          </Badge>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Type Selection */}
                  {selectedCategoryId && (
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-3">
                        Select Service Type *
                      </label>
                      {typesLoading ? (
                        <LoadingState>Loading service types...</LoadingState>
                      ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          {types?.results?.map((type) => (
                            <button
                              key={type.id}
                              type="button"
                              onClick={() => setSelectedTypeId(type.id)}
                              className={`p-4 rounded-lg border text-left transition-all ${
                                selectedTypeId === type.id
                                  ? 'border-[#1173d4] bg-[#1173d4]/10 text-white'
                                  : 'border-[#233648] bg-[#1a2633] text-gray-300 hover:border-[#1173d4]/50'
                              }`}
                            >
                              <div className="font-medium mb-1">{type.type_name}</div>
                              <p className="text-xs text-gray-400">{type.type_description}</p>
                              <Badge size="sm" status="info" className="mt-2">
                                {type.fields_count || 0} fields
                              </Badge>
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Dynamic Fields */}
          {selectedTypeId && (
            <Card>
              <CardContent className="pt-6">
                <h2 className="text-xl font-semibold text-white mb-4">Configuration</h2>

                {fieldsLoading ? (
                  <LoadingState>Loading configuration fields...</LoadingState>
                ) : fields && fields.length > 0 ? (
                  <div className="space-y-4">
                    {fields
                      .sort((a, b) => a.order - b.order)
                      .map((field) => (
                        <div key={field.id}>
                          <label
                            htmlFor={field.field_name}
                            className="block text-sm font-medium text-gray-300 mb-2"
                          >
                            {field.field_name.charAt(0).toUpperCase() + field.field_name.slice(1).replace(/_/g, ' ')}
                            {field.is_required && ' *'}
                            {field.is_secure && (
                              <Badge size="sm" status="warning" className="ml-2">
                                Secure
                              </Badge>
                            )}
                          </label>
                          {renderField(field)}
                          {field.help_text && (
                            <p className="text-xs text-gray-400 mt-1">{field.help_text}</p>
                          )}
                        </div>
                      ))}
                  </div>
                ) : (
                  <p className="text-gray-400">No configuration fields required for this service type.</p>
                )}
              </CardContent>
            </Card>
          )}

          {/* Error Display */}
          {error && (
            <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-3">
            <Link to="/credentials">
              <Button variant="outline">Cancel</Button>
            </Link>
            <Button
              type="submit"
              loading={submitting}
              disabled={!selectedTypeId || submitting}
            >
              Add Credential
            </Button>
          </div>
        </form>
      </div>
    </Layout>
  );
}