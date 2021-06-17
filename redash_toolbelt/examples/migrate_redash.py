import click
import json
import requests

from redash_toolbelt import Redash

def get_source_dashboards_and_queries():
    return None

def get_target_data_source(source_query):
    data_source_mapping = json.load(open('./migration_mapping/data_source_mapping.json'))

    for data_source in data_source_mapping:
        if data_source["source_id"] == source_query["data_source_id"] and not(data_source["target_id"] == -1):
           return data_source["target_id"]


def migrate(source_client, target_client, target_redash_url, target_api_key):
    """Creates a blank dashboard, duplicates the original's queries,
    and populates it with fresh widgets that mirror the original widgets.
    """

    # Copped this logic directly from Redash.duplicate_dashboard
    source_dashboards = source_client.paginate(source_client.dashboards)
    for source_dashboard in source_dashboards:

        dashboard_name = format(source_dashboard["name"])
        # target_dashboard = target_client.create_dashboard(dashboard_name)

        print(f'DASHBOARD NAME: {dashboard_name}')
        print(f'ALL DATA: { source_dashboard}')
        print(f'WIDGETS: {source_dashboard.get("widgets", [])}')
        print(f'TAGS: {source_dashboard["tags"]}')
        # if source_dashboard["tags"]:
            # target_client.update_dashboard(
            #     target_dashboard["id"], {"tags": source_dashboard["tags"]}
            # )

           
        # Widgets can hold text boxes or visualizations. Filter out text boxes.
        # I use a dictionary here because it de-duplicates query IDs
        queries_to_duplicate = {
            widget["visualization"]["query"]["id"]: widget["visualization"]["query"]
            for widget in source_dashboard.get("widgets", [])
            if "visualization" in widget
        }

        # Fetch full query details for the old query IDs
        # Duplicate the query and store the result
        source_vs_target_query_pairs = [
            {
                "source_query": source_client._get(f"api/queries/{source_query.get('id')}").json(),
                "target_query": {
                    "query": source_query["query"],
                    "name": source_query["name"],
                    "data_source_id": get_target_data_source(source_query),
                    "options": source_query["options"]
                },
                # "target_query": requests.post(
                #     target_redash_url + '/api/queries', 
                #     headers = {'Authorization': target_api_key },
                #     json={
                #         "query": source_query["query"],
                #         "name": source_query["name"],
                #         "data_source_id": get_target_data_source(source_query),
                #         "options": source_query["options"]
                #     }
                # ),  
            }
            for source_query in queries_to_duplicate.values()
        ]

        # Compare old visualizations to new ones
        # Create a mapping of old visualization IDs to new ones
        source_viz_vs_target_viz = {
            source_viz.get("id"): target_viz.get("id")
            for pair in source_vs_target_query_pairs
            for source_viz in pair["source_query"].get("visualizations")
            for target_viz in pair["target_query"].get("visualizations")
            if source_viz.get("options") == target_viz.get("options")
        }

        # This is a version of the same logic from Redash.duplicate_dashboard
        # But it substitutes in the new visualiation ID pointing at the copied query.
        for widget in source_dashboard["widgets"]:
            visualization_id = None
            if "visualization" in widget:
                visualization_id = source_viz_vs_target_viz.get(widget["visualization"]["id"])
            # target_client.create_widget(
            #     target_dashboard["id"], visualization_id, widget["text"], widget["options"]
            # )

        print(target_dashboard)
        break


@click.command()
@click.argument("source_redash_url")
@click.argument("target_redash_url")
@click.option(
    "--source-api-key",
    "source_api_key",
    envvar="SOURCE_REDASH_API_KEY",
    show_envvar=True,
    prompt="Source API Key",
    help="The User API Key from the Redash to be migrated from",
)
@click.option(
    "--target-api-key",
    "target_api_key",
    envvar="TARGET_REDASH_API_KEY",
    show_envvar=True,
    prompt="Target API Key",
    help="The User API Key from the Redash to migrate into",
)
def main(source_redash_url, target_redash_url, source_api_key, target_api_key):
    """Calls the duplicate function using Click commands"""

    source_client = Redash(source_redash_url, source_api_key)
    target_client = Redash(target_redash_url, target_api_key)

    migrate(source_client, target_client, target_redash_url, target_api_key)


if __name__ == "__main__":
    main()
