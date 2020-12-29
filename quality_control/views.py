from django.contrib import messages
from quality_control.models import FinalAnnotation
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.edit import UpdateView
from scans.models import Scan
from cradle_of_mankind.decorators import remember_last_query_params
from django.template.defaulttags import register
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from zooniverse.models import Classification, Retirement, Workflow
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


@login_required
@remember_last_query_params('specimen-numbers', ['page', 'workflow', 'status'])
def specimen_numbers_list(request):
    workflows = Workflow.objects.all()
    if request.GET.get('workflow'):
        workflow = Workflow.objects.get(pk=request.GET.get('workflow'))
    else:
        workflow = Workflow.objects.get(pk=6400)
    query = request.GET.get('query')
    status = request.GET.get('status')
    whole_query = f"?query={query}&workflow={workflow.id}&status={status}"
    retirements = get_retirements(request, workflow)
    tasks = get_tasks_for_workflow(workflow)
    values, colors = get_counts_and_colors(retirements, tasks)
    return render(request, 'quality_control/quality_control_list.html',
                  {'workflows': workflows,
                   'current_workflow': workflow,
                   'page_obj': retirements,
                   'tasks': tasks,
                   'values': values,
                   'colors': colors,
                   'status': status,
                   'whole_query': whole_query})


@login_required
def specimen_numbers_check(request, workflow_pk, scan_pk):
    workflow = Workflow.objects.get(pk=workflow_pk)
    scan = Scan.objects.get(id=scan_pk)
    retirement = scan.subject.retirement_set.filter(workflow=workflow).first()
    tasks = get_tasks_for_workflow(workflow)
    other_workflows = get_other_workflows(workflow, scan)

    if request.method == 'POST':
        if 'waiting-btn' in request.POST:
            retirement.status = 'waiting'
            retirement.save()
            messages.success(request, "Status set as waiting")
            return redirect('specimen-numbers-check', scan_pk=scan_pk, workflow_pk=workflow_pk)
        retirement.status = 'checked'
        retirement.save()
        for question in tasks.values():
            answer = request.POST.get(question, None)
            if answer:
                final = FinalAnnotation()
                final.scan = scan
                final.retirement = retirement
                final.question = question
                final.answer = answer
                final.save()
        if 'next-btn' in request.POST:
            retirements = Retirement.objects.filter(workflow=workflow)
            retirements = retirements.filter(status='to be checked')
            retirements = retirements.filter(
                subject__scan__id__gt=scan.id).order_by('subject__scan__id')
            next_retirement = retirements.first().subject.scan
            if next_retirement is None:
                return redirect('specimen-numbers')
            return redirect('specimen-numbers-check', scan_pk=next_retirement.id, workflow_pk=workflow.id)
        return redirect('specimen-numbers')
    checked = retirement.status == 'checked'
    if not checked:
        questions = get_questions_and_values(retirement, tasks)
    else:
        questions = get_final_annotations(retirement, tasks)
    return render(request, 'quality_control/quality_control_check.html',
                  {'scan': scan, 'questions': questions,
                   'checked': checked, 'other_workflows': other_workflows})


def get_retirements(request, workflow):
    query = request.GET.get('query')
    status = request.GET.get('status')
    retirement_list = Retirement.objects.filter(workflow=workflow)
    if status:
        retirement_list = retirement_list.filter(status=status)
    if query:
        try:
            query = int(query)
            scan = Scan.objects.get(pk=query)
            subject = scan.subject
            retirement_list = retirement_list.filter(subject=subject)
        except:
            pass
    retirement_list = retirement_list.order_by('subject__scan__id')

    page = request.GET.get('page', 1)

    paginator = Paginator(retirement_list, 10)

    try:
        retirements = paginator.page(page)
    except PageNotAnInteger:
        retirements = paginator.page(1)
    except EmptyPage:
        retirements = paginator.page(paginator.num_pages)
    return retirements


def get_counts_and_colors(retirements, tasks):
    counts = dict()
    colors = dict()
    for retirement in retirements:
        counts[retirement] = len(retirement.classification_set.all())
        colors[retirement] = []
        for task in tasks:
            classifications = retirement.classification_set.all()
            annotations = []
            for classification in classifications:
                annotations.extend(
                    classification.annotation_set.filter(task=task))
            answer_counts = {}
            for annotation in annotations:
                answer_counts[annotation.value] = answer_counts.get(
                    annotation.value, 0) + 1
            if answer_counts:
                max_count = max(answer_counts.values())
                similarity_score = max_count / len(annotations)
                if similarity_score <= 1/len(annotations):
                    colors[retirement].append('red')
                elif similarity_score < 0.5:
                    colors[retirement].append('orange')
                elif similarity_score < 1:
                    colors[retirement].append('yellow')
                else:
                    colors[retirement].append('green')
            else:
                colors[retirement].append('red')
    return counts, colors


def get_tasks_for_workflow(workflow):
    if workflow.name == 'Specimen Numbers':
        header = ['Pfx', 'AN', 'FN', 'FN (Pre)', 'Shelf',
                  'Date', 'Published', 'Type', 'PTO']
        tasks = ['T9', 'T1', 'T2', 'T5', 'T8', 'T6', 'T3', 'T7', 'T4']
    elif workflow.name == 'Location and stratigraphy':
        header = ['Locality', 'SITE/AREA', 'Formation',
                  'Mbr/Horizon/Etc.', 'Photo', 'Coordinates']
        tasks = ['T0', 'T3', 'T2', 'T1', 'T5', 'T7']
    elif workflow.name == 'Nature of Specimen (Body parts)':
        header = ['Body parts', 'Fragments']
        tasks = ['T0', 'T1']
    elif workflow.name == 'Specimen Taxonomy (Latin names)':
        header = ['Taxon', 'Family', 'Subfamily', 'Tribe', 'Genus', 'Species']
        tasks = ['T0', 'T2', 'T3', 'T1', 'T4', 'T5']
    elif workflow.name == 'Additional info (Card backside)':
        header = ['Reference', 'Coordinates', 'Photo', 'Other']
        tasks = ['T4', 'T5', 'T6', 'T7']
    return {tasks[i]: header[i] for i in range(len(tasks))}


def get_other_workflows(workflow, scan):
    other_workflows = []
    retirements = scan.subject.retirement_set.all()
    all_checked = True
    for r in retirements:
        print(f"{r.workflow.name}: {r.status}")
        if r.status != 'checked':
            all_checked = False
        other_workflows.append((r.workflow, r.status))
    return other_workflows


def summary(request):
    workflows = Workflow.objects.all()
    scan_list = Scan.objects.all()

    page = request.GET.get('page', 1)

    paginator = Paginator(retirement_list, 10)

    try:
        scans = paginator.page(page)
    except PageNotAnInteger:
        scans = paginator.page(1)
    except EmptyPage:
        scans = paginator.page(paginator.num_pages)

    statuses = {}
    for scan in scans:
        workflows_dict = {}
        try:
            retirements = scan.subject.retirement_set.all()
            for workflow in workflows:
                if len(retirements.filter(workflow=workflow)) == 0:
                    workflows_dict[workflow] = 'red'
                else:
                    r = retirements.filter(workflow=workflow).first()
                    if r.status == 'checked':
                        workflows_dict[workflow] = 'green'
                    elif r.status == 'waiting':
                        workflows_dict[workflow] = 'yellow'
                    else:
                        workflows_dict[workflow] = 'red'
        except Subject.DoesNotExist:
            for workflow in workflows:
                workflows_dict[workflow] = 'red'
        statuses[scan] = workflows_dict

    return render(request, 'quality_control/quality_control_summary.html',
                  {'workflows': workflows,
                   'statuses': statuses,
                   'page_obj': scans})


def get_final_annotations(retirement, tasks):
    questions = []
    annotations = FinalAnnotation.objects.filter(retirement=retirement)
    for task, name, in tasks.items():
        annotation = annotations.filter(question=name).first()
        if annotation:
            answers = {annotation.answer: 1}
            color = 'grey'
            questions.append({name: [answers, color, 1]})
    return questions


def get_questions_and_values(retirement, tasks):
    questions = []
    for task, name in tasks.items():
        classifications = retirement.classification_set.all()
        annotations = []
        for classification in classifications:
            annotations.extend(
                classification.annotation_set.filter(task=task))
        answers = {}
        for annotation in annotations:
            answers[annotation.value] = answers.get(
                annotation.value, 0) + 1
        answers = {k: v for k, v in sorted(
            answers.items(), key=lambda item: item[1], reverse=True)}
        if answers:
            max_count = max(answers.values())
            similarity_score = max_count / len(annotations)
            if similarity_score <= 1/len(annotations):
                color = 'red'
            elif similarity_score <= 0.5:
                color = 'orange'
            elif similarity_score < 1:
                color = 'yellow'
            else:
                color = 'green'
        else:
            answers[''] = 1
            color = 'red'
        first_value = get_first_value(answers)
        questions.append({name: [answers, color, first_value]})
    return questions


def get_first_value(dictionary):
    values = dictionary.keys()
    iterator = iter(values)
    first_value = next(iterator)
    return first_value


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)
