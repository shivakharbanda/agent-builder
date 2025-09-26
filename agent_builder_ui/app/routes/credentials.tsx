import React, { useState } from 'react';
import { Link } from 'react-router';
import type { Route } from './+types/credentials';
import { Layout } from '../components/layout/Layout';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { LoadingState, EmptyState } from '../components/ui/Loading';
import { useCredentials, useCredentialCategories } from '../hooks/useAPI';
import { api } from '../lib/api';
import { formatRelativeTime } from '../lib/utils';
import type { CredentialCategory } from '../lib/types';

export function meta({}: Route.MetaArgs) {
  return [
    { title: "Credentials - Agent Builder" },
    { name: "description", content: "Manage your service credentials and API keys" },
  ];
}

export default function Credentials() {
  const { data: credentials, loading, refetch } = useCredentials();
  const { data: categories } = useCredentialCategories();
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  const handleDelete = async (credentialId: number, credentialName: string) => {
    if (!confirm(`Are you sure you want to delete "${credentialName}"? This action cannot be undone.`)) {
      return;
    }

    try {
      setDeleting(true);
      setDeleteId(credentialId);
      await api.deleteCredential(credentialId);
      await refetch(); // Refresh the list
    } catch (error) {
      console.error('Failed to delete credential:', error);
      // TODO: Show error toast
    } finally {
      setDeleting(false);
      setDeleteId(null);
    }
  };

  const handleRestore = async (credentialId: number, credentialName: string) => {
    if (!confirm(`Are you sure you want to restore "${credentialName}"?`)) {
      return;
    }

    try {
      setDeleting(true);
      setDeleteId(credentialId);
      await api.restoreCredential(credentialId);
      await refetch(); // Refresh the list
    } catch (error) {
      console.error('Failed to restore credential:', error);
      // TODO: Show error toast
    } finally {
      setDeleting(false);
      setDeleteId(null);
    }
  };

  // Filter credentials by category
  const filteredCredentials = credentials?.results?.filter(credential => {
    if (selectedCategory === 'all') return true;
    return credential.credential_type_name?.includes(selectedCategory);
  }) || [];

  // Get category display name
  const getCategoryDisplayName = (categoryName: string) => {
    const category = categories?.results?.find(c => c.name.toLowerCase() === categoryName.toLowerCase());
    return category?.name || categoryName;
  };

  return (
    <Layout>
      <div className="mx-auto max-w-7xl">
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-white text-3xl font-bold leading-tight tracking-tight">
              Credentials
            </h1>
            <p className="text-gray-400 mt-1">
              Manage your service credentials, API keys, and database connections.
            </p>
          </div>
          <Link to="/credentials/create">
            <Button
              leftIcon={<span className="material-symbols-outlined text-base">key</span>}
            >
              Add Credential
            </Button>
          </Link>
        </div>

        {/* Category Filter */}
        {categories?.results && (
          <div className="mb-6 flex gap-2 flex-wrap">
            <Button
              size="sm"
              variant={selectedCategory === 'all' ? 'solid' : 'outline'}
              onClick={() => setSelectedCategory('all')}
            >
              All
            </Button>
            {categories.results.map((category) => (
              <Button
                key={category.id}
                size="sm"
                variant={selectedCategory === category.name.toLowerCase() ? 'solid' : 'outline'}
                onClick={() => setSelectedCategory(category.name.toLowerCase())}
                leftIcon={
                  category.icon ? (
                    <span className="material-symbols-outlined text-sm">{category.icon}</span>
                  ) : undefined
                }
              >
                {category.name}
              </Button>
            ))}
          </div>
        )}

        {/* Credentials List */}
        {loading ? (
          <LoadingState>Loading credentials...</LoadingState>
        ) : !filteredCredentials?.length ? (
          <EmptyState
            title="No credentials yet"
            description="Add your first credential to connect to external services and APIs"
            icon={
              <span className="material-symbols-outlined text-4xl">vpn_key</span>
            }
            action={
              <Link to="/credentials/create">
                <Button
                  leftIcon={<span className="material-symbols-outlined text-base">key</span>}
                >
                  Add Your First Credential
                </Button>
              </Link>
            }
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredCredentials.map((credential) => (
              <Card key={credential.id} className="hover:bg-[#1f2937] transition-colors">
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className="text-lg font-semibold text-white">
                          {credential.name}
                        </h3>
                        {credential.is_deleted && (
                          <Badge status="error" size="sm">
                            Deleted
                          </Badge>
                        )}
                      </div>
                      <p className="text-gray-400 text-sm mt-1 line-clamp-2">
                        {credential.description || 'No description provided'}
                      </p>
                    </div>
                    <Badge status="info">
                      {credential.credential_type_name}
                    </Badge>
                  </div>

                  <div className="mt-4 flex items-center gap-4 text-sm text-gray-500">
                    <div className="flex items-center gap-1">
                      <span className="material-symbols-outlined text-sm">settings</span>
                      <span>{credential.details_count || 0} fields</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <span className="material-symbols-outlined text-sm">
                        {credential.is_deleted ? 'delete' : 'check_circle'}
                      </span>
                      <span>{credential.is_deleted ? 'Deleted' : 'Active'}</span>
                    </div>
                  </div>

                  <div className="mt-4 pt-4 border-t border-[#233648] flex items-center justify-between">
                    <span className="text-xs text-gray-500">
                      Created {formatRelativeTime(credential.created_at)}
                    </span>
                    <div className="flex gap-2">
                      {credential.is_deleted ? (
                        <Button
                          size="sm"
                          variant="outline"
                          color="green"
                          onClick={() => handleRestore(credential.id, credential.name)}
                          loading={deleting && deleteId === credential.id}
                          disabled={deleting}
                        >
                          <span className="material-symbols-outlined text-sm">restore</span>
                          Restore
                        </Button>
                      ) : (
                        <>
                          <Link to={`/credentials/${credential.id}/edit`}>
                            <Button size="sm" variant="outline">
                              <span className="material-symbols-outlined text-sm">edit</span>
                              Edit
                            </Button>
                          </Link>
                          <Button
                            size="sm"
                            variant="outline"
                            color="red"
                            onClick={() => handleDelete(credential.id, credential.name)}
                            loading={deleting && deleteId === credential.id}
                            disabled={deleting}
                          >
                            <span className="material-symbols-outlined text-sm">delete</span>
                          </Button>
                        </>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Pagination */}
        {credentials && credentials.count > 20 && (
          <div className="mt-8 flex justify-center">
            <p className="text-gray-400 text-sm">
              Showing {filteredCredentials.length} of {credentials.count} credentials
            </p>
          </div>
        )}
      </div>
    </Layout>
  );
}