import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import type { Route } from './+types/$id.edit';
import { Layout } from '../../components/layout/Layout';
import { Card, CardContent } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Badge } from '../../components/ui/Badge';
import { LoadingState } from '../../components/ui/Loading';
import { useCredential, useCredentialTypeFields, useFormSubmit } from '../../hooks/useAPI';
import { api } from '../../lib/api';
import type { CredentialField, CredentialUpdate } from '../../lib/types';

export function meta({}: Route.MetaArgs) {
  return [
    { title: "Edit Credential - Agent Builder" },
    { name: "description", content: "Edit an existing service credential" },
  ];
}

interface FormData {
  name: string;
  description: string;
  credential_details: Record<string, string>;
}

export default function EditCredential() {
  const navigate = useNavigate();
  const { id } = useParams();
  const credentialId = parseInt(id || '0');

  const { data: credential, loading: credentialLoading, error: credentialError } = useCredential(credentialId);
  const { data: fields, loading: fieldsLoading } = useCredentialTypeFields(credential?.credential_type || null);

  const [formData, setFormData] = useState<FormData>({
    name: '',
    description: '',
    credential_details: {}
  });

  const { submit, loading: submitting, error } = useFormSubmit((data: CredentialUpdate) => api.updateCredential(credentialId, data));

  // Populate form data when credential loads
  useEffect(() => {
    if (credential) {
      setFormData({
        name: credential.name,
        description: credential.description,
        credential_details: credential.details?.reduce((acc, detail) => {
          // Don't populate secure fields with masked values
          if (detail.is_secure && detail.value === '***MASKED***') {
            acc[detail.field_name || ''] = '';
          } else {
            acc[detail.field_name || ''] = detail.value;
          }
          return acc;
        }, {} as Record<string, string>) || {}
      });
    }
  }, [credential]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.name.trim()) {
      alert('Please enter a name for the credential');
      return;
    }

    // Validate required fields
    if (fields) {
      const requiredFields = fields.filter(field => field.is_required);
      const missingFields = requiredFields.filter(field => {
        const value = formData.credential_details[field.field_name];
        // For secure fields, allow empty values (means "don't change")
        if (field.is_secure && !value) {
          return false;
        }
        return !value?.trim();
      });

      if (missingFields.length > 0) {
        alert(`Please fill in all required fields: ${missingFields.map(f => f.field_name).join(', ')}`);
        return;
      }
    }

    // Filter out empty credential details (for secure fields that shouldn't be updated)
    const filteredDetails: Record<string, string> = {};
    Object.entries(formData.credential_details).forEach(([key, value]) => {
      if (value && value.trim()) {
        filteredDetails[key] = value;
      }
    });

    const updateData: CredentialUpdate = {
      name: formData.name,
      description: formData.description,
      credential_details: Object.keys(filteredDetails).length > 0 ? filteredDetails : undefined
    };

    try {
      await submit(updateData);
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
      placeholder: field.is_secure && !value ? 'Leave empty to keep current value' : (field.placeholder || `Enter ${field.field_name}`),
      required: field.is_required && !field.is_secure, // Don't require secure fields in edit mode
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

  if (credentialLoading) {
    return (
      <Layout>
        <div className="mx-auto max-w-4xl">
          <LoadingState>Loading credential...</LoadingState>
        </div>
      </Layout>
    );
  }

  if (credentialError || !credential) {
    return (
      <Layout>
        <div className="mx-auto max-w-4xl">
          <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
            <p className="text-red-400">
              {credentialError || 'Credential not found'}
            </p>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="mx-auto max-w-4xl">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-2 text-sm text-gray-400 mb-2">
            <Link to="/credentials" className="hover:text-white">Credentials</Link>
            <span>/</span>
            <span>{credential.name}</span>
            <span>/</span>
            <span>Edit</span>
          </div>
          <h1 className="text-white text-3xl font-bold leading-tight tracking-tight">
            Edit Credential
          </h1>
          <p className="text-gray-400 mt-1">
            Update your {credential.credential_type_name} credential configuration.
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

          {/* Service Type Info (Read-only) */}
          <Card>
            <CardContent className="pt-6">
              <h2 className="text-xl font-semibold text-white mb-4">Service Type</h2>
              <div className="p-4 bg-[#233648]/30 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <Badge status="info">{credential.credential_type_name}</Badge>
                  <span className="text-gray-400 text-sm">
                    Service type cannot be changed after creation
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Dynamic Fields */}
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
                          {field.is_required && !field.is_secure && ' *'}
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
                        {field.is_secure && (
                          <p className="text-xs text-amber-400 mt-1">
                            Leave empty to keep the current value. Enter a new value to update.
                          </p>
                        )}
                      </div>
                    ))}
                </div>
              ) : (
                <p className="text-gray-400">No configuration fields available for this service type.</p>
              )}
            </CardContent>
          </Card>

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
              disabled={submitting}
            >
              Update Credential
            </Button>
          </div>
        </form>
      </div>
    </Layout>
  );
}